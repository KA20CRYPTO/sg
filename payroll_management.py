import streamlit as st
import os
import json
from datetime import datetime
import pandas as pd
import requests
import plotly.express as px

# --- FIRESTORE UTILITIES (Duplicated from employee_management for independence) ---
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw')
FIREBASE_PROJECT_ID = globals().get('__app_id', 'screenerproapp')
FIRESTORE_BASE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"

def convert_to_firestore_fields(data):
    firestore_fields = {}
    for key, value in data.items():
        if isinstance(value, str):
            firestore_fields[key] = {"stringValue": value}
        elif isinstance(value, bool):
            firestore_fields[key] = {"booleanValue": value}
        elif isinstance(value, int):
            firestore_fields[key] = {"integerValue": str(value)}
        elif isinstance(value, float):
            firestore_fields[key] = {"doubleValue": value}
        elif isinstance(value, datetime):
            firestore_fields[key] = {"timestampValue": value.isoformat() + "Z"}
        elif isinstance(value, list):
            firestore_fields[key] = {"arrayValue": {"values": [convert_to_firestore_fields_single(item) for item in value]}}
        elif isinstance(value, dict):
            firestore_fields[key] = {"mapValue": {"fields": convert_to_firestore_fields(value)}}
        elif value is None:
            firestore_fields[key] = {"nullValue": None}
        else:
            firestore_fields[key] = {"stringValue": str(value)}
    return firestore_fields

def convert_to_firestore_fields_single(value):
    if isinstance(value, str):
        return {"stringValue": value}
    elif isinstance(value, bool):
        return {"booleanValue": value}
    elif isinstance(value, int):
        return {"integerValue": str(value)}
    elif isinstance(value, float):
        return {"doubleValue": value}
    elif isinstance(value, datetime):
        return {"timestampValue": value.isoformat() + "Z"}
    elif isinstance(value, list):
        return {"arrayValue": {"values": [convert_to_firestore_fields_single(item) for item in value]}}
    elif isinstance(value, dict):
        return {"mapValue": {"fields": convert_to_firestore_fields(value)}}
    elif value is None:
        return {"nullValue": None}
    else:
        return {"stringValue": str(value)}

def parse_firestore_document(doc_data):
    parsed_data = {}
    if "fields" in doc_data:
        for key, value_obj in doc_data["fields"].items():
            if "stringValue" in value_obj:
                parsed_data[key] = value_obj["stringValue"]
            elif "integerValue" in value_obj:
                parsed_data[key] = int(value_obj["integerValue"])
            elif "doubleValue" in value_obj:
                parsed_data[key] = float(value_obj["doubleValue"])
            elif "booleanValue" in value_obj:
                parsed_data[key] = value_obj["booleanValue"]
            elif "timestampValue" in value_obj:
                parsed_data[key] = datetime.fromisoformat(value_obj["timestampValue"].replace('Z', '+00:00'))
            elif "arrayValue" in value_obj and "values" in value_obj["arrayValue"]:
                parsed_data[key] = [parse_firestore_document_single(item) for item in value_obj["arrayValue"]["values"]]
            elif "mapValue" in value_obj and "fields" in value_obj["mapValue"]:
                parsed_data[key] = parse_firestore_document({"fields": value_obj["mapValue"]["fields"]})
            elif "nullValue" in value_obj:
                parsed_data[key] = None
    if "name" in doc_data:
        parsed_data["id"] = doc_data["name"].split("/")[-1]
    return parsed_data

def parse_firestore_document_single(value_obj):
    if "stringValue" in value_obj:
        return value_obj["stringValue"]
    elif "integerValue" in value_obj:
        return int(value_obj["integerValue"])
    elif "doubleValue" in value_obj:
        return float(value_obj["doubleValue"])
    elif "booleanValue" in value_obj:
        return value_obj["booleanValue"]
    elif "timestampValue" in value_obj:
        return datetime.fromisoformat(value_obj["timestampValue"].replace('Z', '+00:00'))
    elif "arrayValue" in value_obj and "values" in value_obj["arrayValue"]:
        return [parse_firestore_document_single(item) for item in value_obj["arrayValue"]["values"]]
    elif "mapValue" in value_obj and "fields" in value_obj["mapValue"]:
        return parse_firestore_document({"fields": value_obj["mapValue"]["fields"]})
    elif "nullValue" in value_obj:
        return None
    return None

def get_documents_from_firestore(collection_path):
    try:
        get_url = f"{FIRESTORE_BASE_URL}/{collection_path}?key={FIREBASE_WEB_API_KEY}"
        response = requests.get(get_url)
        response.raise_for_status()
        data = response.json()
        if 'documents' in data:
            return [parse_firestore_document(doc) for doc in data['documents']]
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch documents from {collection_path}: {e.response.text if e.response else e}")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return []

def add_document_to_firestore(collection_path, doc_data):
    try:
        add_url = f"{FIRESTORE_BASE_URL}/{collection_path}?key={FIREBASE_WEB_API_KEY}"
        doc_data["created_at"] = datetime.now()
        response = requests.post(add_url, json={"fields": convert_to_firestore_fields(doc_data)})
        if response.status_code != 200:
            st.error(f"Firestore Error ({response.status_code}): {response.text}")
        response.raise_for_status()
        return response.json().get('name', '').split('/')[-1]
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to add document: {e.response.text if e.response else e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

def update_document_in_firestore(collection_path, doc_id, doc_data):
    """Updates specific fields in a Firestore document using PATCH."""
    try:
        update_url = f"{FIRESTORE_BASE_URL}/{collection_path}/{doc_id}?key={FIREBASE_WEB_API_KEY}&updateMask.fieldPaths={'&updateMask.fieldPaths='.join(doc_data.keys())}"
        response = requests.patch(update_url, json={"fields": convert_to_firestore_fields(doc_data)})
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to update document: {e.response.text if e.response else e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return False

def get_employee_collection_path(user_company):
    sanitized_company = user_company.replace(' ', '_').lower()
    return f"artifacts/{FIREBASE_PROJECT_ID}/employee_management_data/{sanitized_company}/employees"

def get_employees_from_firestore(user_company):
    return get_documents_from_firestore(get_employee_collection_path(user_company))

def get_payroll_collection_path(user_company):
    sanitized_company = user_company.replace(' ', '_').lower()
    return f"artifacts/{FIREBASE_PROJECT_ID}/employee_management_data/{sanitized_company}/payroll"

def get_claims_collection_path(user_company):
    sanitized_company = user_company.replace(' ', '_').lower()
    return f"artifacts/{FIREBASE_PROJECT_ID}/employee_management_data/{sanitized_company}/claims"

def get_config_collection_path(user_company):
    sanitized_company = user_company.replace(' ', '_').lower()
    return f"artifacts/{FIREBASE_PROJECT_ID}/employee_management_data/{sanitized_company}/payroll_config"

# --- PAYROLL PAGE ---

def payroll_management_page():
    st.title("Payroll Management")
    st.markdown("Process monthly salaries, manage deductions, and track financial disbursements.")

    user_company = st.session_state.get('user_company', 'default_company')
    if not user_company:
        user_company = 'default_company'
    sanitized_user_company = str(user_company).replace(' ', '_').lower()
    dark_mode = st.session_state.get('dark_mode_main', False)
    primary_color = '#00cec9'
    secondary_bg = '#262730' if dark_mode else '#F0F2F6'
    card_bg = '#3A3A3A' if dark_mode else '#FFFFFF'
    text_color_main = '#f0f2f6' if dark_mode else '#333333'
    text_color_light = '#BBBBBB' if dark_mode else '#555555'

    # Fetch employees once for use in multiple tabs
    employees = get_employees_from_firestore(sanitized_user_company)
    
    st.markdown(f"*Active Company Context: **{user_company}***")
    
    # Tabs for different payroll actions
    tabs = st.tabs(["Run Payroll", "Claims Log", "Payroll History", "Financial Dashboard", "Configuration"])

    with tabs[0]:
        st.subheader("Process Monthly Payroll")
        
        # Step 1: Select Period
        col_m, col_y = st.columns(2)
        with col_m:
            month = st.selectbox("Month", ["January", "February", "March", "April", "May", "June", 
                                          "July", "August", "September", "October", "November", "December"])
        with col_y:
            year = st.selectbox("Year", [2023, 2024, 2025, 2026])

        # Step 2: Fetch and Configure Adjustments
        active_employees = [e for e in employees if str(e.get('status', e.get('employment_status', ''))).strip().capitalize() == "Active"]
        
        if not active_employees:
            st.warning(f"No active employees found to process payroll (Found {len(employees)} total).")
        else:
            # Pre-fetch claims to show in the adjustment table
            claims_docs = get_documents_from_firestore(get_claims_collection_path(sanitized_user_company))
            approved_claims = [c for c in claims_docs if c.get('status') == 'Approved' and not c.get('processed')]

            st.markdown("### Monthly Adjustments")
            st.info("Adjust variable pay or leave deductions for this period before generating.")
            
            # Prepare data for editing
            adjustment_data = []
            for emp in active_employees:
                emp_id = emp.get('id')
                emp_claims = [c for c in approved_claims if c.get('employee_id') == emp_id]
                total_reimbursements = sum([float(c.get('amount', 0)) for c in emp_claims])

                adjustment_data.append({
                    "id": emp_id,
                    "Name": emp.get('name'),
                    "Department": emp.get('department', 'N/A'),
                    "Base Salary (Annual)": float(emp.get('salary', 0.0)),
                    "Variable Bonus (₹)": 0.0,
                    "LWP Days": 0,
                    "Pending Reimbursements (₹)": total_reimbursements
                })
            
            df_adj = pd.DataFrame(adjustment_data)
            edited_df = st.data_editor(
                df_adj,
                column_config={
                    "id": None, # Hide ID
                    "Base Salary (Annual)": st.column_config.NumberColumn(format="₹%.2f", disabled=True),
                    "Variable Bonus (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                    "LWP Days": st.column_config.NumberColumn(min_value=0, max_value=31),
                    "Pending Reimbursements (₹)": st.column_config.NumberColumn(format="₹%.2f", disabled=True)
                },
                use_container_width=True,
                key="payroll_adj_editor",
                hide_index=True
            )

            if st.button("Generate & Disburse Payroll", use_container_width=True):
                # Fetch Config (Claims already fetched above)
                config_docs = get_documents_from_firestore(get_config_collection_path(sanitized_user_company))
                conf = config_docs[0] if config_docs else {"hra_percent": 40, "pf_percent": 12, "prof_tax": 200}

                # Fetch existing records for this period to prevent duplicates
                all_records = get_documents_from_firestore(get_payroll_collection_path(sanitized_user_company))
                period_str = f"{month} {year}"
                processed_emp_ids = [r.get('employee_id') for r in all_records if r.get('period_name') == period_str]

                progress_bar = st.progress(0)
                count = 0
                skip_count = 0
                total = len(active_employees)
                
                for idx, row in edited_df.iterrows():
                    emp_id = row['id']
                    
                    if emp_id in processed_emp_ids:
                        skip_count += 1
                        continue
                    # Get full employee object for breakdown and bank details
                    emp_obj = next((e for e in active_employees if e.get('id') == emp_id), {})
                    if not isinstance(emp_obj, dict): emp_obj = {}
                    breakdown = emp_obj.get('salary_breakdown', {})
                    if not isinstance(breakdown, dict): breakdown = {}
                    
                    # Reimbursements already calculated in adjustment table for visibility
                    total_reimbursements = float(row.get("Pending Reimbursements (₹)", 0))
                    emp_claims = [c for c in approved_claims if c.get('employee_id') == emp_id]
                    
                    # 1. Earnings
                    monthly_base = float(breakdown.get('base', row['Base Salary (Annual)'])) / 12
                    monthly_hra = monthly_base * (float(conf.get('hra_percent', 40)) / 100)
                    monthly_allowances = float(breakdown.get('allowances', 0.0)) / 12
                    variable_bonus = float(row['Variable Bonus (₹)'])
                    
                    gross_earnings = monthly_base + monthly_hra + monthly_allowances + variable_bonus + total_reimbursements
                    
                    # 2. Deductions
                    lwp_deduction = (gross_earnings / 30) * int(row['LWP Days'])
                    epf_deduction = monthly_base * (float(conf.get('pf_percent', 12)) / 100)
                    prof_tax = float(conf.get('prof_tax', 200)) if row['Base Salary (Annual)'] > 0 else 0.0
                    
                    # Simple Net Pay: Gross - Deductions (No complex tax as requested)
                    total_deductions = lwp_deduction + epf_deduction + prof_tax
                    net_pay = gross_earnings - total_deductions
                    
                    payroll_data = {
                        "employee_id": emp_id,
                        "employee_name": row['Name'],
                        "bank_details": {
                            "account_no": emp_obj.get('bank_account', 'N/A'),
                            "ifsc": emp_obj.get('ifsc_code', 'N/A')
                        },
                        "period_name": f"{month} {year}",
                        "period_end": f"{year}-{month}-01",
                        "department": row['Department'],
                        "status": "Paid",
                        "payout_date": datetime.now().isoformat(),
                        "company_info": {
                            "name": conf.get('company_name', user_company),
                            "address": conf.get('company_address', "")
                        },
                        "earnings": {
                            "base": monthly_base,
                            "hra": monthly_hra,
                            "allowances": monthly_allowances,
                            "variable_bonus": variable_bonus,
                            "reimbursements": total_reimbursements
                        },
                        "deductions": {
                            "lwp": lwp_deduction,
                            "epf": epf_deduction,
                            "professional_tax": prof_tax
                        },
                        "gross_pay": gross_earnings,
                        "total_deductions": total_deductions,
                        "net_pay": net_pay
                    }
                    
                    add_document_to_firestore(get_payroll_collection_path(sanitized_user_company), payroll_data)
                    
                    # Mark claims as processed
                    for claim in emp_claims:
                        update_document_in_firestore(get_claims_collection_path(sanitized_user_company), claim['id'], {"processed": True})
                    
                    count += 1
                    progress_bar.progress(count/total)
                
                if count > 0:
                    st.success(f"Finalized payroll for {count} employees. Period: {month} {year}")
                if skip_count > 0:
                    st.warning(f"Skipped {skip_count} employees who already had payroll records for {month} {year}.")
                
                if count == 0 and skip_count > 0:
                    st.info("No new payroll records were generated as all selected employees were already processed.")
                elif count == 0:
                    st.error("No payroll records were generated.")

    with tabs[1]:
        st.subheader("Claims and Reimbursements Log")
        st.markdown("Manually record or manage expense claims for employees.")
        
        if not employees:
            st.warning("No employees found. Please add employees in the Employee Management page first.")
        else:
            # Form to add a new claim
            with st.expander("Record New Claim"):
                with st.form("new_claim_form"):
                    employee_names_list = [e['name'] for e in employees]
                    claim_emp = st.selectbox("Employee", options=employee_names_list, key="claim_emp_select")
                    claim_cat = st.selectbox("Category", ["Travel", "Medical", "Internet/Remote Work", "Training", "Other"])
                    claim_amt = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
                    claim_date = st.date_input("Claim Date", datetime.now().date())
                    claim_desc = st.text_area("Description")
                    
                    if st.form_submit_button("Log Claim"):
                        emp_id = next((e['id'] for e in employees if e['name'] == claim_emp), None)
                        claim_data = {
                            "employee_id": emp_id,
                            "employee_name": claim_emp,
                            "category": claim_cat,
                            "amount": claim_amt,
                            "date": claim_date.isoformat(),
                            "description": claim_desc,
                            "status": "Approved", # Defaulting to approved for HR manual entry
                            "processed": False
                        }
                        if add_document_to_firestore(get_claims_collection_path(sanitized_user_company), claim_data):
                            st.success(f"Claim for {claim_emp} logged successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to log claim for {claim_emp}. Check error details above.")

        # Display existing claims
        claims = get_documents_from_firestore(get_claims_collection_path(sanitized_user_company))
        if claims:
            df_claims = pd.DataFrame(claims)
            st.dataframe(df_claims[["employee_name", "category", "amount", "date", "status", "processed"]], use_container_width=True, hide_index=True)
        else:
            st.info("No claims recorded yet.")

    with tabs[2]:
        st.subheader("Payroll History and Digital Payslips")
        records = get_documents_from_firestore(get_payroll_collection_path(sanitized_user_company))
        if records:
            df_history = pd.DataFrame(records).sort_values(by="period_end", ascending=False)
            
            col_search, col_export = st.columns([3, 1])
            with col_search:
                search_query = st.text_input("Search by employee name or period", "")
            
            filtered_history = df_history
            if search_query:
                filtered_history = df_history[
                    df_history['employee_name'].str.contains(search_query, case=False, na=False) |
                    df_history['period_name'].str.contains(search_query, case=False, na=False)
                ]
            
            with col_export:
                csv = filtered_history.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Export to CSV",
                    data=csv,
                    file_name=f"payroll_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv',
                    use_container_width=True
                )
            
            required_cols = ['employee_name', 'period_name', 'gross_pay', 'total_deductions', 'net_pay', 'payout_date']
            display_df = filtered_history.reindex(columns=required_cols)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("View Detailed Payslip")
            selected_record_idx = st.selectbox(
                "Select a record to view full breakdown:",
                options=filtered_history.index,
                format_func=lambda x: f"{filtered_history.loc[x, 'employee_name']} - {filtered_history.loc[x, 'period_name']}"
            )
            
            if selected_record_idx is not None:
                rec_match = filtered_history.loc[selected_record_idx]
                # loc can return a DataFrame if indices are duplicated, or a Series for a single row.
                if isinstance(rec_match, pd.DataFrame):
                    rec = rec_match.iloc[0].to_dict()
                elif isinstance(rec_match, pd.Series):
                    rec = rec_match.to_dict()
                else:
                    st.error("Could not parse payroll record. The data might be corrupted.")
                    st.stop()
                co_info = rec.get('company_info', {})
                if not isinstance(co_info, dict): co_info = {}
                bank = rec.get('bank_details', {})
                if not isinstance(bank, dict): bank = {}
                
                # Ensure earnings and deductions are also dicts for calculations in the template
                earn = rec.get('earnings', {})
                if not isinstance(earn, dict): earn = {}
                deduc = rec.get('deductions', {})
                if not isinstance(deduc, dict): deduc = {}
                
                st.markdown(f"""
                <div style="background-color: {card_bg}; padding: 30px; border-radius: 15px; border: 1px solid {primary_color};">
                    <h2 style="text-align: center; color: {primary_color}; margin-bottom:0;">{co_info.get('name', 'Electronic Payslip')}</h2>
                    <p style="text-align: center; color: {text_color_light}; margin-top:0;">{co_info.get('address', '')}</p>
                    <p style="text-align: center; font-weight: bold; color: {text_color_main};">Pay Slip - {rec['period_name']}</p>
                    <hr>
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <p><strong>Employee:</strong> {rec['employee_name']}</p>
                            <p><strong>Department:</strong> {rec['department']}</p>
                            <p><strong>Bank A/c:</strong> {bank.get('account_no', 'N/A')} | <strong>IFSC:</strong> {bank.get('ifsc', 'N/A')}</p>
                        </div>
                        <div style="text-align: right;">
                            <p><strong>Status:</strong> {rec['status']}</p>
                            <p><strong>Payout Date:</strong> {rec['payout_date'][:10]}</p>
                        </div>
                    </div>
                    <hr>
                    <div style="display: flex; gap: 40px;">
                        <div style="flex: 1;">
                            <h4 style="color: {primary_color};">Earnings</h4>
                            <table style="width: 100%; color: {text_color_main};">
                                <tr><td>Base</td><td style="text-align: right;">₹{earn.get('base', 0):,.2f}</td></tr>
                                <tr><td>HRA</td><td style="text-align: right;">₹{earn.get('hra', 0):,.2f}</td></tr>
                                <tr><td>Allowances</td><td style="text-align: right;">₹{earn.get('allowances', 0):,.2f}</td></tr>
                                <tr><td>Variable Bonus</td><td style="text-align: right;">₹{earn.get('variable_bonus', 0):,.2f}</td></tr>
                                <tr><td>Reimbursements</td><td style="text-align: right; color:#27ae60;">₹{earn.get('reimbursements', 0):,.2f}</td></tr>
                                <tr style="font-weight: bold; border-top: 1px solid {text_color_light};">
                                    <td>Total Earnings</td><td style="text-align: right;">₹{rec.get('gross_pay', 0):,.2f}</td>
                                </tr>
                            </table>
                        </div>
                        <div style="flex: 1;">
                            <h4 style="color: #ff7675;">Deductions</h4>
                            <table style="width: 100%; color: {text_color_main};">
                                <tr><td>PF</td><td style="text-align: right;">₹{deduc.get('epf', 0):,.2f}</td></tr>
                                <tr><td>Prof. Tax</td><td style="text-align: right;">₹{deduc.get('professional_tax', 0):,.2f}</td></tr>
                                <tr><td>LWP Deduction</td><td style="text-align: right;">₹{deduc.get('lwp', 0):,.2f}</td></tr>
                                <tr style="font-weight: bold; border-top: 1px solid {text_color_light};">
                                    <td>Total Deductions</td><td style="text-align: right;">₹{rec.get('total_deductions', 0):,.2f}</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                    <hr>
                    <div style="text-align: center; padding: 15px; background-color: {secondary_bg}; border-radius: 10px;">
                        <h3 style="margin: 0; color: {primary_color};">Net Pay: ₹{rec.get('net_pay', 0):,.2f}</h3>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No payroll records found.")

    with tabs[3]:
        st.subheader("Financial Dashboard")
        if records:
            df = pd.DataFrame(records)
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Total Net Payout", f"₹{df.get('net_pay', pd.Series([0])).sum():,.2f}")
            with m2:
                st.metric("Total Gross", f"₹{df.get('gross_pay', pd.Series([0])).sum():,.2f}")
            with m3:
                st.metric("Total Deductions", f"₹{df.get('total_deductions', pd.Series([0])).sum():,.2f}")
            
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                fig_dist = px.pie(df, values='net_pay', names='department', title="Pay by Department", hole=0.4, template="plotly_white")
                st.plotly_chart(fig_dist, use_container_width=True)
            with col_c2:
                req_agg_cols = ['period_name', 'gross_pay', 'net_pay', 'total_deductions']
                df_agg_safe = df.reindex(columns=req_agg_cols).fillna(0)
                agg_pay = df_agg_safe.groupby('period_name')[['gross_pay', 'net_pay', 'total_deductions']].sum().reset_index()
                fig_compare = px.bar(agg_pay, x='period_name', y=['net_pay', 'total_deductions'], title="Gross vs Net Comparison", barmode='stack', template="plotly_white")
                st.plotly_chart(fig_compare, use_container_width=True)
        else:
            st.info("Insufficient data for visualizations.")

    with tabs[4]:
        st.subheader("Payroll Configuration")
        st.markdown("Customize percentages for salary components and other global settings.")
        
        config_docs = get_documents_from_firestore(get_config_collection_path(sanitized_user_company))
        current_config = config_docs[0] if config_docs else {
            "hra_percent": 40,
            "pf_percent": 12,
            "prof_tax": 200,
            "company_name": user_company,
            "company_address": "",
            "currency": "₹"
        }
        
        with st.form("config_form"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                hra_p = st.number_input("HRA % of Basic", value=current_config.get("hra_percent", 40))
                pf_p = st.number_input("PF % of Basic", value=current_config.get("pf_percent", 12))
            with col_c2:
                p_tax = st.number_input("Professional Tax (Monthly)", value=current_config.get("prof_tax", 200))
                c_name = st.text_input("Company Name for Payslip", value=current_config.get("company_name", user_company))
            
            c_addr = st.text_area("Company Address", value=current_config.get("company_address", ""))
            
            if st.form_submit_button("Save Configuration"):
                new_config = {
                    "hra_percent": hra_p,
                    "pf_percent": pf_p,
                    "prof_tax": p_tax,
                    "company_name": c_name,
                    "company_address": c_addr,
                    "currency": "₹"
                }
                # Since we don't have an 'update' document helper here, we use a simple add for now or a custom logic.
                # For this demo, we'll just add it. In a real app, you'd update specific doc ID.
                add_document_to_firestore(get_config_collection_path(sanitized_user_company), new_config)
                st.success("Configuration updated.")
                st.rerun()
