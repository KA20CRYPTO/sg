import streamlit as st
import requests
import pandas as pd
import datetime
import uuid

# ==========================================================
# IMPORTS FROM YOUR EXISTING SYSTEM
# ==========================================================
# NOTE: These imports are assumed to exist in your environment
# from firebase_config import FIRESTORE_DOCUMENTS_URL, FIREBASE_WEB_API_KEY
# from activation_email import send_activation_email

from firebase_config import FIRESTORE_DOCUMENTS_URL, FIREBASE_WEB_API_KEY
from activation_email import send_activation_email

def send_activation_email(email, name, link):
    print(f"Mock: Sending activation email to {email} ({name}) with link: {link}")


# ==========================================================
# SETTINGS
# ==========================================================
ADMIN_EMAILS = {
    "screenerpro.ai@gmail.com",
    "manav.nagpal2005@gmail.com"
}
ADMIN_PASSWORD = "Mahadev@1234"


# ==========================================================
# UTILS
# ==========================================================
def firestore_format(data: dict):
    """Convert python dict -> Firestore REST fields format."""
    fields = {}
    for k, v in data.items():
        if isinstance(v, str):
            fields[k] = {"stringValue": v}
        elif isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        elif isinstance(v, int):
            fields[k] = {"integerValue": str(v)}
        elif v is None:
            fields[k] = {"nullValue": None}
        else:
            fields[k] = {"stringValue": str(v)}
    return {"fields": fields}


def fs_patch(path, data: dict):
    """
    Firestore REST TRUE MERGE PATCH
    """
    base_url = f"{FIRESTORE_DOCUMENTS_URL}/{path}"
    masks = "&".join([f"updateMask.fieldPaths={k}" for k in data.keys()])

    url = f"{base_url}?key={FIREBASE_WEB_API_KEY}&{masks}"

    payload = {
        "fields": {}
    }

    for k, v in data.items():
        if isinstance(v, str):
            payload["fields"][k] = {"stringValue": v}
        elif isinstance(v, bool):
            payload["fields"][k] = {"booleanValue": v}
        elif isinstance(v, int):
            payload["fields"][k] = {"integerValue": str(v)}
        elif v is None:
            payload["fields"][k] = {"nullValue": None}
        else:
            payload["fields"][k] = {"stringValue": str(v)}

    r = requests.patch(url, json=payload)
    return r.status_code in (200, 201)


def fs_delete(path):
    try:
        url = f"{FIRESTORE_DOCUMENTS_URL}/{path}?key={FIREBASE_WEB_API_KEY}"
        r = requests.delete(url)
        return r.status_code in (200, 204)
    except:
        return False


def fs_write_subcollection(path, data):
    """Write a doc in a subcollection with random ID."""
    try:
        doc_id = str(uuid.uuid4())
        url = f"{FIRESTORE_DOCUMENTS_URL}/{path}/{doc_id}?key={FIREBASE_WEB_API_KEY}"
        r = requests.patch(url, json=firestore_format(data))
        return r.status_code in (200, 201)
    except:
        return False


# ✅ FIX 1: Robust reader for Firestore REST API.
def get_field(f, k, default=""):
    """
    Safe reader for Firestore REST API.
    Handles missing fields, empty mapValue, nullValue, etc.
    """
    if k not in f:
        return default

    v = f[k]

    # Strings
    if "stringValue" in v:
        return v["stringValue"]

    # Boolean
    if "booleanValue" in v:
        return v["booleanValue"]

    # Integer
    if "integerValue" in v:
        # Convert integer strings to actual int
        try:
            return int(v["integerValue"])
        except ValueError:
            return default # Fallback if conversion fails

    # NULL
    if "nullValue" in v:
        return default

    # Firestore sometimes returns empty mapValue: {}
    if "mapValue" in v:
        # Check for nested fields structure which may contain the actual value
        fields = v["mapValue"].get("fields", {})
        if "value" in fields:
            # Handle possible stringValue inside the nested value
            return fields["value"].get("stringValue", default)
        return default # Return default if mapValue is empty or structure is unexpected

    # Fallback for any other type, or if value is just {}
    return default


# ==========================================================
# FIRESTORE FETCH (CACHED)
# ==========================================================
@st.cache_data(ttl=300, show_spinner=False) # ⭐ TTL set to 300 seconds (5 minutes)
def fetch_collection(path):
    try:
        url = f"{FIRESTORE_DOCUMENTS_URL}/{path}?key={FIREBASE_WEB_API_KEY}"
        r = requests.get(url)
        if r.status_code != 200:
            return []
        return r.json().get("documents", [])
    except:
        return []


@st.cache_data(ttl=300, show_spinner=False) # ⭐ TTL set to 300 seconds (5 minutes)
def fetch_user_docs():
    """Fetch both pending and verified users."""
    users = []

    # Pending users
    for doc in fetch_collection("pending_users"):
        f = doc.get("fields", {})
        doc_id = doc["name"].split("/")[-1]
        users.append({
            "id": doc_id,
            "path": f"pending_users/{doc_id}",
            "name": get_field(f, "name"),
            "email": get_field(f, "email"),
            "company": get_field(f, "company"),
            "status": "pending",
            "isVerified": False,
            "activation_token": get_field(f, "activation_token"),
            "type": "pending",
            # NEW activity fields (if present in Firestore)
            "created_at": get_field(f, "created_at"),
            "verified_at": get_field(f, "verified_at"),
            "last_login": get_field(f, "last_login"),
        })

    # Verified users
    for doc in fetch_collection("user_profiles"):
        f = doc.get("fields", {})
        doc_id = doc["name"].split("/")[-1]
        users.append({
            "id": doc_id,
            "path": f"user_profiles/{doc_id}",
            "name": get_field(f, "name"),
            "email": get_field(f, "email"),
            "company": get_field(f, "company"),
            "status": get_field(f, "status", "active"),
            "isVerified": True,
            "activation_token": "",
            "type": "verified",
            # NEW activity fields
            "created_at": get_field(f, "created_at"),
            "verified_at": get_field(f, "verified_at"),
            "last_login": get_field(f, "last_login"),
        })

    return users


def clear_cache():
    fetch_user_docs.clear()
    fetch_collection.clear()


# ==========================================================
# AUDIT LOGS
# ==========================================================
def log_admin_action(user_id, action, admin_email, details=""):
    path = f"user_profiles/{user_id}/audit_logs"
    data = {
        "action": action,
        "admin": admin_email,
        "details": details,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    fs_write_subcollection(path, data)


def get_audit_logs(user_id):
    logs = fetch_collection(f"user_profiles/{user_id}/audit_logs")
    output = []
    for doc in logs:
        f = doc.get("fields", {})
        output.append({
            "action": get_field(f, "action"),
            "admin": get_field(f, "admin"),
            "details": get_field(f, "details"),
            "timestamp": get_field(f, "timestamp")
        })
    output.sort(key=lambda x: x["timestamp"], reverse=True)
    return output


# ==========================================================
# LOGIN HISTORY & USER ACTIVITY
# ==========================================================
def log_user_login(user_id: str):
    """
    Log a user login event and update last_login timestamp.
    """
    now_iso = datetime.datetime.utcnow().isoformat()

    # Append to login_history subcollection
    path = f"user_profiles/{user_id}/login_history"
    data = {
        "timestamp": now_iso
    }
    fs_write_subcollection(path, data)

    # Update last_login on main user profile document
    fs_patch(f"user_profiles/{user_id}", {
        "last_login": now_iso
    })


def get_login_history(user_id: str):
    logs = fetch_collection(f"user_profiles/{user_id}/login_history")
    output = []
    for doc in logs:
        f = doc.get("fields", {})
        output.append({
            "timestamp": get_field(f, "timestamp")
        })
    output.sort(key=lambda x: x["timestamp"], reverse=True)
    return output


def fetch_all_login_history(df_users):
    """Load all login history with ALWAYS correct name/email/company."""

    user_map = {}

    for _, row in df_users.iterrows():
        # Ensure no NaN or empty values
        clean_name = row["name"] if row["name"] else row["email"].split("@")[0]
        clean_email = row["email"]
        # Use safe check for company, which should now be read correctly as "" if empty
        clean_company = row["company"] if row["company"] else ""

        user_map[row["id"]] = {
            "name": clean_name,
            "email": clean_email,
            "company": clean_company
        }

    all_logs = []

    # Now collect login history
    for user_id, udata in user_map.items():
        logs = fetch_collection(f"user_profiles/{user_id}/login_history")

        for entry in logs:
            f = entry.get("fields", {})
            ts = get_field(f, "timestamp")

            if ts:
                all_logs.append({
                    "user_id": user_id,
                    "name": udata["name"],
                    "email": udata["email"],
                    "company": udata["company"],
                    "timestamp": ts
                })

    all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return all_logs


# ==========================================================
# AUTH: ADMIN LOGIN
# ==========================================================
def admin_login():
    if st.session_state.get("admin_logged_in"):
        return True

    st.title("🔐 ScreenerPro Admin Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        if email in ADMIN_EMAILS and pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.session_state.admin_email = email
            st.rerun()
        else:
            st.error("❌ Wrong credentials")

    return False


# ==========================================================
# NOTIFICATIONS: Pending Users
# ==========================================================
def render_admin_notifications(df):
    
    # ✅ FIX 3: Safely check for 'type' column existence to prevent KeyError
    if df.empty or 'type' not in df.columns:
        pending_count = 0
    else:
        pending_count = len(df[df["type"] == "pending"])
        
    if pending_count > 0:
        st.warning(f"⚠️ {pending_count} users are pending approval. Review them now.")


# ==========================================================
# USER MANAGEMENT SIDEBAR
# ==========================================================
def render_user_sidebar(user):
    st.sidebar.title("Manage User")
    st.sidebar.write(f"**{user['name']}**")
    st.sidebar.write(f"📧 {user['email']}")
    st.sidebar.write(f"🏢 {user['company'] if user['company'] else 'N/A'}")

    # --------------- USER ACTIVITY BLOCK ---------------
    st.sidebar.subheader("User Activity")

    created_at = user.get("created_at") or "-"
    verified_at = user.get("verified_at") or "-"
    last_login = user.get("last_login") or "-"

    st.sidebar.write(f"🕒 Created At: `{created_at}`")
    st.sidebar.write(f"✅ Verified At: `{verified_at}`")
    st.sidebar.write(f"📌 Last Login: `{last_login}`")

    st.sidebar.markdown("---")

    # LOGIN HISTORY (only meaningful for verified users / if history exists)
    st.sidebar.subheader("Login History")
    if user["type"] == "verified":
        history = get_login_history(user["id"])
        if not history:
            st.sidebar.write("No login history yet.")
        else:
            # show latest 10
            for h in history[:10]:
                st.sidebar.write(f"➡️ `{h['timestamp']}`")
    else:
        st.sidebar.write("Login history available after account is verified.")

    st.sidebar.markdown("---")

    # --------------- EDIT USER ---------------
    st.sidebar.subheader("Edit")
    with st.sidebar.form("edit_user_form"):
        new_name = st.text_input("Name", user["name"])
        new_company = st.text_input("Company", user["company"])
        new_status = st.selectbox(
            "Status",
            ["pending", "active", "suspended"],
            index=["pending", "active", "suspended"].index(user["status"])
        )
        save = st.form_submit_button("Save Changes")

        if save:
            update = {
                "name": new_name,
                "company": new_company,
                "status": new_status
            }
            fs_patch(user["path"], update)
            log_admin_action(user["id"], "UPDATE_USER", st.session_state.admin_email, details=f"Name: {new_name}, Company: {new_company}, Status: {new_status}")
            clear_cache()
            st.rerun()

    st.sidebar.subheader("Actions")

    # PENDING USER ACTIONS
    if user["type"] == "pending":
        if st.sidebar.button("Approve User"):
            now_iso = datetime.datetime.utcnow().isoformat()
            
            # Update pending_users document
            fs_patch(user["path"], {
                "isVerified": True,
                "status": "active",
                "verified_at": now_iso
            })
            
            log_admin_action(user["id"], "APPROVE_USER", st.session_state.admin_email)
            
            clear_cache()
            st.success("Approved!")
            st.rerun()

        if st.sidebar.button("Resend Activation Email"):
            link = f"https://screenerpro.streamlit.app/?activate={user['activation_token']}&email={user['email']}"
            send_activation_email(user["email"], user["name"], link)
            st.sidebar.success("Email sent!")

    # VERIFIED USER ACTIONS
    else:
        if user["status"] != "suspended" and st.sidebar.button("Suspend User"):
            fs_patch(user["path"], {"status": "suspended"})
            log_admin_action(user["id"], "SUSPEND_USER", st.session_state.admin_email)
            clear_cache()
            st.rerun()
        
        if user["status"] == "suspended" and st.sidebar.button("Re-activate User"):
            fs_patch(user["path"], {"status": "active"})
            log_admin_action(user["id"], "REACTIVATE_USER", st.session_state.admin_email)
            clear_cache()
            st.rerun()

        if st.sidebar.button("Delete User", help="This action is irreversible."):
            fs_delete(user["path"])
            log_admin_action(user["id"], "DELETE_USER", st.session_state.admin_email)
            clear_cache()
            st.session_state.selected_user = None
            st.rerun()

    # AUDIT LOGS
    st.sidebar.subheader("Audit Logs")
    logs = get_audit_logs(user["id"])
    for log in logs:
        st.sidebar.write(f"🕒 `{log['timestamp'].split('.')[0].replace('T', ' ')}`\n**{log['action']}** by {log['admin']}")


# ==========================================================
# COMPANY MANAGEMENT PAGE
# ==========================================================
def render_company_management(df):
    st.header("🏢 Company Management")

    # ✅ FIX 2: Use a copy of the full DataFrame and ensure company is treated as string.
    df_clean = df.copy() 
    df_clean['company'] = df_clean['company'].fillna('') # Treat NaNs as empty string ("")

    # Separate users with a company name (where company is not "")
    # This uses .astype(bool) CORRECTLY, only for partitioning the data, not for filtering the main list.
    df_with_company = df_clean[df_clean["company"].astype(bool)]
    
    # Get unique list of companies that actually have a name
    companies = df_with_company["company"].unique()
    
    data = []
    
    # Process companies that have a name
    if companies.size > 0:
        for c in companies:
            users = df_with_company[df_with_company["company"] == c]
            verified = len(users[users["type"] == "verified"])
            pending = len(users[users["type"] == "pending"])
            total = len(users)
            data.append([c, total, verified, pending])
            
    # Add a row for users without a company name
    no_company_users = df_clean[~df_clean["company"].astype(bool)]
    if not no_company_users.empty:
        no_verified = len(no_company_users[no_company_users["type"] == "verified"])
        no_pending = len(no_company_users[no_company_users["type"] == "pending"])
        data.append(["**[No Company Listed]**", len(no_company_users), no_verified, no_pending])
            
    if not data:
        st.info("No users found to display in Company Management.")
        return

    df_comp = pd.DataFrame(data, columns=["Company", "Total Users", "Verified", "Pending"])
    st.dataframe(df_comp, use_container_width=True)

    st.subheader("Company-Wise Users")
    
    # Use all unique values (including empty strings) for the selectbox
    all_company_options = df_clean["company"].unique().tolist()
    # Sort and replace the empty string with a descriptive label for the user
    all_company_options = sorted([c if c else "[No Company Listed]" for c in all_company_options])
    
    company_selected_label = st.selectbox("Select Company", all_company_options)

    # Map the label back to the actual string value for filtering
    company_selected_value = "" if company_selected_label == "[No Company Listed]" else company_selected_label

    if company_selected_value is not None:
        st.dataframe(
            df_clean[df_clean["company"] == company_selected_value][["name", "email", "status", "last_login"]], 
            use_container_width=True
        )


# ==========================================================
# ANALYTICS PAGE
# ==========================================================
def render_analytics(df):
    st.header("📊 Analytics")

    # Ensure activity columns exist even if some rows miss them
    if "last_login" not in df.columns:
        df["last_login"] = ""

    # Parse last_login timestamps and compute "active in last 24h"
    def parse_ts(ts):
        if not ts:
            return None
        try:
            # Handle ISO format with or without microseconds/timezone info
            return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return None

    df_copy = df.copy()
    # Apply UTC timezone to comparison time for consistency
    now_utc = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    
    # Ensure parsed timestamps are timezone-aware (or converted to UTC)
    df_copy["last_login_dt"] = df_copy["last_login"].apply(parse_ts).apply(
        lambda x: x.replace(tzinfo=datetime.timezone.utc) if x and x.tzinfo is None else x
    )

    def is_active_24h(ts):
        if ts is None:
            return False
        # Calculate difference using timezone-aware objects
        return (now_utc - ts).total_seconds() <= 24 * 3600

    active_24h = df_copy["last_login_dt"].apply(is_active_24h).sum()

    if df.empty or 'type' not in df.columns:
        total_users = 0
        verified_users = 0
        pending_users = 0
        vf = pd.DataFrame()
    else:
        total_users = len(df)
        verified_users = len(df[df["type"] == "verified"])
        pending_users = len(df[df["type"] == "pending"])
        vf = df[df["type"] == "verified"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Users", total_users)
    c2.metric("Verified Users", verified_users)
    c3.metric("Pending Users", pending_users)
    c4.metric("Active Users (last 24h)", int(active_24h))

    st.subheader("Status Breakdown (Verified Only)")
    
    if not vf.empty:
        st.bar_chart(vf["status"].value_counts())
    else:
        st.info("No verified users yet to show status breakdown.")


# ==========================================================
# USER LIST
# ==========================================================
def render_user_list(df, title):
    st.subheader(f"{title} ({len(df)})")

    if df.empty:
        st.info(f"No {title.lower()} found.")
        return

    for _, user in df.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([6, 1])
            with col1:
                st.write(f"### {user['name']}")
                st.write(f"📧 {user['email']} | 🏢 {user['company'] if user['company'] else 'N/A'}")
                
                status_line = f"Status: **{user['status']}**"
                if user.get("last_login"):
                    # Displaying only date and time, cleaning up T and Z/offset
                    login_time_clean = user['last_login'].split('.')[0].replace('T', ' ')
                    status_line += f" | Last Login (UTC): `{login_time_clean}`"
                
                # Show Creation/Verification date for context
                if user.get("created_at"):
                    created_time_clean = user['created_at'].split('.')[0].replace('T', ' ')
                    status_line += f" | Created (UTC): `{created_time_clean}`"

                st.write(status_line)

            with col2:
                if st.button("Manage", key=f"manage_{user['path']}"):
                    st.session_state.selected_user = user.to_dict()
                    st.rerun()


# ==========================================================
# MAIN ADMIN PANEL UI
# ==========================================================
def admin_panel():
    st.title("🛠 ScreenerPro Admin Panel")
    st.caption(f"Logged in as: {st.session_state.admin_email}")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.divider()
    
    # Clear cache button for manual refresh
    if st.button("Refresh Data (Clear Cache)"):
        clear_cache()
        st.rerun()

    df = pd.DataFrame(fetch_user_docs())

    # --- Start Fix 3 ---
    # Create a safe DataFrame (df_safe) for filtering operations to prevent KeyError: 'type' 
    # if the main df is empty and has no columns.
    if df.empty or 'type' not in df.columns:
        # Create a DataFrame with necessary columns and 0 rows
        df_safe = pd.DataFrame(columns=[
            "id", "path", "name", "email", "company", 
            "status", "isVerified", "activation_token", "type", 
            "created_at", "verified_at", "last_login"
        ])
    else:
        df_safe = df.copy()
    # --- End Fix 3 ---


    # Notifications
    render_admin_notifications(df_safe)

    # Search (must run on the original df for accurate results, but check column existence)
    query = st.text_input("🔎 Search users")
    if query:
        # Check for column existence before filtering
        if 'name' in df.columns and 'email' in df.columns and 'company' in df.columns:
            df = df[
                df["name"].astype(str).str.contains(query, case=False, na=False)
                | df["email"].astype(str).str.contains(query, case=False, na=False)
                | df["company"].astype(str).str.contains(query, case=False, na=False)
            ]
        # If columns don't exist, df is likely empty/safe, but we skip filtering for safety.


    # Render Sidebar if a user is selected
    if st.session_state.get("selected_user"):
        # Find the latest data for the selected user to avoid stale information
        current_id = st.session_state.selected_user["id"]
        # Use df_safe for lookups to ensure the column exists
        filtered_df = df_safe[df_safe["id"] == current_id]
        if not filtered_df.empty:
            latest_user = filtered_df.iloc[0].to_dict() 
        else:
            latest_user = st.session_state.selected_user

        render_user_sidebar(latest_user)

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Pending Users",
        "Verified Users",
        "Company Management",
        "Analytics",
        "Overall Login History"
    ])

    with tab1:
        # Use df_safe for safe filtering
        pending_df = df_safe[df_safe["type"] == "pending"]
        render_user_list(pending_df, "Pending Users")

    with tab2:
        # Use df_safe for safe filtering
        verified_df = df_safe[df_safe["type"] == "verified"]
        render_user_list(verified_df, "Verified Users")

    with tab3:
        render_company_management(df_safe)

    with tab4:
        render_analytics(df_safe)

    with tab5:
        st.header("📜 Overall Login History")

        # Pass df_safe to the fetch history function
        logs = fetch_all_login_history(df_safe)

        if not logs:
            st.info("No login events yet.")
        else:
            df_logs = pd.DataFrame(logs)
            
            # ... (rest of the tab5 logic) ...

            # Convert UTC → datetime
            df_logs["timestamp_dt_utc"] = pd.to_datetime(df_logs["timestamp"])

            # Convert to IST (UTC + 5:30)
            ist_offset = datetime.timedelta(hours=5, minutes=30)
            df_logs["timestamp_dt"] = df_logs["timestamp_dt_utc"] + ist_offset

            # Extract useful fields
            df_logs["date"] = df_logs["timestamp_dt"].dt.date
            df_logs["day"] = df_logs["timestamp_dt"].dt.day_name()
            df_logs["hour"] = df_logs["timestamp_dt"].dt.hour
            df_logs["timestamp_ist"] = df_logs["timestamp_dt"].dt.strftime("%Y-%m-%d %I:%M:%S %p IST")

            # ----------------------------
            # 🔍 FILTERS
            # ----------------------------
            st.subheader("Filters")

            filter_option = st.selectbox(
                "Filter By",
                ["All", "Today", "Last 7 Days", "Last 30 Days"],
                key="login_filter_option"
            )

            # Base time for comparison in IST
            now_ist = datetime.datetime.utcnow() + ist_offset

            df_logs_filtered = df_logs.copy()

            if filter_option == "Today":
                today = now_ist.date()
                df_logs_filtered = df_logs[df_logs["timestamp_dt"].dt.date == today]

            elif filter_option == "Last 7 Days":
                limit = now_ist - datetime.timedelta(days=7)
                df_logs_filtered = df_logs[df_logs["timestamp_dt"] >= limit]

            elif filter_option == "Last 30 Days":
                limit = now_ist - datetime.timedelta(days=30)
                df_logs_filtered = df_logs[df_logs["timestamp_dt"] >= limit]

            # Search filter
            search = st.text_input("Search by name, email or company")

            if search:
                df_logs_filtered = df_logs_filtered[
                    df_logs_filtered["name"].fillna("").str.contains(search, case=False)
                    | df_logs_filtered["email"].fillna("").str.contains(search, case=False)
                    | df_logs_filtered["company"].fillna("").str.contains(search, case=False)
                ]

            # ----------------------------
            # 📈 INSIGHTS
            # ----------------------------
            st.subheader("📈 Summary Insights")
            
            if df_logs_filtered.empty:
                 st.info("No login events match the current filters.")
                 return

            total_logins = len(df_logs_filtered)
            unique_users = df_logs_filtered["email"].nunique()
            
            # Use .mode() to find the most frequent value, handle empty result
            top_company_series = df_logs_filtered["company"].value_counts()
            top_company = top_company_series.index[0] if not top_company_series.empty else "-"
            
            most_active_day_series = df_logs_filtered["day"].value_counts()
            most_active_day = most_active_day_series.index[0] if not most_active_day_series.empty else "-"


            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Login Events", total_logins)
            c2.metric("Unique Users", unique_users)
            c3.metric("Most Active Company", top_company)
            c4.metric("Most Active Day", most_active_day)

            st.divider()

            # ----------------------------
            # 👑 TOP ACTIVE USERS
            # ----------------------------
            st.subheader("🏆 Top 10 Active Users")

            top_users = (
                df_logs_filtered.groupby(["name", "email", "company"])
                .size()
                .reset_index(name="Login Count")
                .sort_values("Login Count", ascending=False)
                .head(10)
            )
            st.dataframe(top_users, use_container_width=True)

            st.divider()

            # ----------------------------
            # 📅 DAILY TREND (IST)
            # ----------------------------
            st.subheader("📅 Daily Login Trend (IST)")
            
            daily_counts = (
                df_logs_filtered.groupby("date")
                .size()
                .reset_index(name="Login Count")
                .sort_values("date")
            )
            st.line_chart(daily_counts, x="date", y="Login Count")

            st.divider()

            # ----------------------------
            # ⏰ HOURLY ACTIVITY
            # ----------------------------
            st.subheader("⏰ Hourly Activity (IST)")

            # Create a full hour range for a complete chart, even for missing hours
            full_hours = pd.Series(0, index=range(0, 24), name="Login Count")
            
            hourly_counts_agg = (
                df_logs_filtered.groupby("hour")
                .size()
                .reset_index(name="Login Count")
                .set_index("hour")
            )
            
            # Combine the full hour range with actual counts
            hourly_counts_combined = full_hours.add(hourly_counts_agg["Login Count"], fill_value=0).reset_index()
            hourly_counts_combined.columns = ["hour", "Login Count"]
            
            st.bar_chart(hourly_counts_combined, x="hour", y="Login Count")

            st.divider()

            # ----------------------------
            # 🧊 DAY OF WEEK
            # ----------------------------
            st.subheader("🧊 Activity by Day of Week")

            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            day_counts = (
                df_logs_filtered.groupby("day")
                .size()
                .reindex(day_order)
                .fillna(0) # Fill missing days with 0
                .reset_index(name="Login Count")
            )
            st.bar_chart(day_counts, x="day", y="Login Count")

            st.divider()

            # ----------------------------
            # RAW LOGIN TABLE
            # ----------------------------
            st.subheader("Raw Login Data (IST)")
            st.dataframe(
                df_logs_filtered[["name", "email", "company", "timestamp_ist"]],
                use_container_width=True
            )


# ==========================================================
# MAIN
# ==========================================================
def main():
    st.set_page_config(page_title="ScreenerPro Admin", layout="wide")
    if admin_login():
        admin_panel()


if __name__ == "__main__":
    main()
