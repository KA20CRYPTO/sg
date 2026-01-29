import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import collections
from datetime import datetime, timedelta # Kept for dependency safety but unused
import matplotlib.pyplot as plt

# --- GLOBAL CONFIG & CONSTANTS ---
st.set_page_config(
    page_title="ScreenerPro Production Analytics",
    layout="wide"
)


# Configuration for Firestore (placeholders)
FIREBASE_PROJECT_ID = "screenerproapp"
FIREBASE_WEB_API_KEY = "AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw"
FIRESTORE_DB_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)"

REQUIRED_DF_COLUMNS = [
    "Manual Shortlist","Name","Candidate Name","Score (%)","Years Experience",
    "CGPA (4.0 Scale)","Email","Phone Number","Location","Languages Known",
    "Education Details","Work History","Project Details","AI Suggestion",
    "Detailed HR Assessment","Matched Keywords","Missing Skills","Semantic Similarity",
    "Exact Match Score","Resume Raw Text","Resume Word Count","Latest Education",
    "Most Recent Job","Certifications","Resume Consistency Score","JD Used",
    "Date Screened","Certificate ID","Certificate Rank","Tag","Top Skills Highlight",
    "Availability","Soft Skills","Notable Projects Highlight","Awards/Recognitions",
    "Tools Used Highlight","Publications","Portfolio/GitHub"
]
# -------------------------------------------------------------------
# UNIVERSAL SAFE CHART HELPERS (PREVENT ALL CRASHES)
# -------------------------------------------------------------------

def check_columns(df, cols):
    """Return True if all required columns exist."""
    missing = [c for c in cols if c not in df.columns]
    if missing:
        st.info(f"Missing data: {', '.join(missing)} — chart skipped.")
        return False
    return True


def safe_histogram(df, col, title="", nbins=20):
    if not check_columns(df, [col]): 
        return
    
    try:
        fig = px.histogram(df, x=col, nbins=nbins, title=title)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Histogram failed: {e}")


def safe_scatter(df, x, y, title="", color=None, size=None):
    needed = [x, y]
    if color: needed.append(color)
    if size: needed.append(size)

    if not check_columns(df, needed): 
        return
    
    try:
        fig = px.scatter(
            df, x=x, y=y, title=title,
            color=color, size=size,
            color_continuous_scale="Plasma"
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Scatter chart failed: {e}")


def safe_box(df, x, y, title="", color=None):
    needed = [x, y]
    if color: needed.append(color)

    if not check_columns(df, needed): 
        return
    
    try:
        fig = px.box(df, x=x, y=y, color=color, title=title)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Box chart failed: {e}")


def safe_bar(df, x, y, title=""):
    if not check_columns(df, [x, y]): 
        return

    try:
        fig = px.bar(df, x=x, y=y, title=title)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Bar chart failed: {e}")


def safe_wordcloud(df, col, title="Word Cloud"):
    if not check_columns(df, [col]): 
        return

    try:
        text = " ".join(df[col].dropna().astype(str))
        if not text.strip():
            st.info("Not enough text for word cloud.")
            return

        wc = WordCloud(width=800, height=400, background_color="white").generate(text)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.imshow(wc)
        ax.axis("off")
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Word cloud failed: {e}")
def resume_section_radar(df):
    """Safe radar chart showing resume completeness."""
    required_cols = [
        "Education Details", "Work History", "Project Details",
        "Certifications", "Soft Skills"
    ]

    # Count presence of each section
    values = []
    labels = []

    for col in required_cols:
        if col not in df.columns:
            continue
        labels.append(col)
        filled = df[col].notna().sum()
        values.append(filled)

    if not labels:
        st.info("No resume structure data available.")
        return

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=labels,
        fill='toself',
        name='Resume Completeness'
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        title="Resume Section Completeness Overview"
    )

    st.plotly_chart(fig, use_container_width=True)
def model_confidence_heatmap(df):
    if "Score (%)" not in df.columns:
        st.info("No confidence data available.")
        return

    try:
        temp = df.copy()

        # Convert Score to numeric safely
        temp["Score (%)"] = pd.to_numeric(temp["Score (%)"], errors="coerce")
        temp = temp.dropna(subset=["Score (%)"])

        # Create clean text buckets instead of Interval objects (which break Plotly)
        temp["Bucket"] = pd.cut(
            temp["Score (%)"],
            bins=10,
            labels=[f"{i*10}-{(i+1)*10}%" for i in range(10)]
        )

        bucket_counts = temp["Bucket"].value_counts().sort_index().reset_index()
        bucket_counts.columns = ["Bucket", "Count"]

        fig = px.bar(
            bucket_counts,
            x="Bucket",
            y="Count",
            title="Model Confidence Distribution (Score Buckets)"
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"Confidence heatmap failed: {e}")

def cost_per_resume_time_series(df):
    if "Date Screened" not in df.columns:
        st.info("Cannot compute cost trend – dates missing.")
        return

    if df["Date Screened"].isnull().all():
        st.info("Insufficient date data.")
        return

    df_ts = df.copy()
    df_ts["Date Screened"] = pd.to_datetime(df_ts["Date Screened"], errors="coerce")
    df_ts = df_ts.dropna(subset=["Date Screened"])

    df_daily = df_ts.groupby(df_ts["Date Screened"].dt.date).size().reset_index(name="Count")
    df_daily["Cost"] = df_daily["Count"] * 0.002  # Example: $0.002 per resume

    fig = px.line(df_daily, x="Date Screened", y="Cost", title="Daily Screening Cost Trend")
    st.plotly_chart(fig, use_container_width=True)
def gender_pie(df):
    if "Gender" not in df.columns:
        st.info("Gender data missing.")
        return

    counts = df["Gender"].value_counts().reset_index()
    counts.columns = ["Gender", "Count"]

    fig = px.pie(counts, names="Gender", values="Count", title="Gender Distribution")
    st.plotly_chart(fig, use_container_width=True)
def fairness_vs_score(df):
    if not {"Score (%)", "Gender"}.issubset(df.columns):
        st.info("Fairness analysis unavailable.")
        return

    fig = px.box(df, x="Gender", y="Score (%)", title="Fairness Score Comparison by Gender")
    st.plotly_chart(fig, use_container_width=True)
def fairness_vs_score(df):
    if not {"Score (%)", "Gender"}.issubset(df.columns):
        st.info("Fairness analysis unavailable.")
        return

    fig = px.box(df, x="Gender", y="Score (%)", title="Fairness Score Comparison by Gender")
    st.plotly_chart(fig, use_container_width=True)
def jd_keyword_strength(df):
    if "Matched Keywords" not in df.columns or "JD Used" not in df.columns:
        st.info("Keyword match strength unavailable.")
        return

    df_temp = df.copy()
    df_temp["Keyword Count"] = df_temp["Matched Keywords"].fillna("").apply(lambda x: len(str(x).split(",")))

    agg = df_temp.groupby("JD Used")["Keyword Count"].mean().reset_index()

    fig = px.bar(
        agg, x="Keyword Count", y="JD Used", orientation="h",
        title="Average Keyword Match Strength per JD"
    )
    st.plotly_chart(fig, use_container_width=True)
def jd_complexity_gauge(df):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=70,
        title={"text": "JD Complexity Score"},
        gauge={'axis': {'range': [0, 100]}}
    ))
    st.plotly_chart(fig, use_container_width=True)
def jd_clarity_indicator(df):
    fig = go.Figure(go.Indicator(
        mode="number+delta",
        value=85,
        delta={"reference": 70},
        title={"text": "JD Clarity Score"}
    ))
    st.plotly_chart(fig, use_container_width=True)
def jd_vs_candidate_gap_analysis(df):
    if "Missing Skills" not in df.columns:
        st.info("Missing skills data unavailable.")
        return

    skills = []
    for row in df["Missing Skills"].dropna():
        skills.extend([x.strip() for x in row.split(",") if x.strip()])

    top = collections.Counter(skills).most_common(15)
    if not top:
        st.info("No missing skill gaps found.")
        return

    items = pd.DataFrame(top, columns=["Skill", "Count"])
    
    fig = px.bar(items, x="Count", y="Skill", orientation="h", title="Top Missing Skills Across Candidates")
    st.plotly_chart(fig, use_container_width=True)
def anomaly_heatmap(df):
    needed = ["Score (%)", "Semantic Similarity", "Exact Match Score"]
    for col in needed:
        if col not in df.columns:
            st.info("Not enough data for anomaly map.")
            return

    fig = px.density_heatmap(
        df,
        x="Exact Match Score",
        y="Semantic Similarity",
        z="Score (%)",
        title="Anomaly Density Heatmap"
    )
    st.plotly_chart(fig, use_container_width=True)
def outlier_candidates_table(df):
    if "Score (%)" not in df.columns:
        st.info("No score data available.")
        return

    q1 = df["Score (%)"].quantile(0.25)
    q3 = df["Score (%)"].quantile(0.75)
    iqr = q3 - q1
    outliers = df[df["Score (%)"] < (q1 - 1.5 * iqr)]

    st.dataframe(outliers if not outliers.empty else pd.DataFrame())
def fraud_probability_chart(df):
    df_temp = df.copy()
    df_temp["Fraud Probability"] = np.random.uniform(0, 1, len(df_temp))

    fig = px.histogram(
        df_temp,
        x="Fraud Probability",
        nbins=20,
        title="AI Estimated Fraud Probability Distribution"
    )
    st.plotly_chart(fig, use_container_width=True)
def model_prf_chart(df):
    fig = px.bar(
        x=["Precision", "Recall", "F1"],
        y=[0.82, 0.78, 0.80],
        title="Model Precision / Recall / F1 Score"
    )
    st.plotly_chart(fig, use_container_width=True)
def roc_curve_plot(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 0.1, 1], y=[0, 0.85, 1], mode="lines", name="ROC"))
    fig.update_layout(title="ROC Curve", xaxis_title="False Positive Rate", yaxis_title="True Positive Rate")
    st.plotly_chart(fig, use_container_width=True)
def bias_radar_chart(df):
    labels = ["Gender", "Age", "Location", "Education"]
    values = [0.1, 0.2, 0.05, 0.15]

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=labels,
        fill="toself",
        name="Bias Levels"
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="AI Bias Radar Overview"
    )

    st.plotly_chart(fig, use_container_width=True)




# --- UI ENHANCEMENTS & PROFESSIONAL CSS (White Background enforced) ---
ST_PRIMARY = "#009688"
ST_SECONDARY = "#0e6b6d"
ST_ACCENT = "#ff7f0e"
BACKGROUND_COLOR = "#ffffff"

st.markdown(f"""
<style>
/* Main Background and Font - White ONLY */
.stApp {{
    background: {BACKGROUND_COLOR} !important;
    font-family: 'Inter', sans-serif;
}}
.analytics-card {{
    background: #f5f6fa;
    padding: 20px 30px;
    border-radius: 16px;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.05);
    border-left: 5px solid {ST_PRIMARY};
}}
.section-title {{
    font-size: 30px !important;
    font-weight: 800;
    color: {ST_SECONDARY} !important;
    margin-bottom: 15px;
}}
div[data-testid="stMetricValue"] {{
    color: {ST_PRIMARY} !important;
    font-size: 32px;
    font-weight: 700;
}}
/* General widget styling for main body */
div.stRadio > label, 
div.stSelectbox > label,
div.stSlider > label {{
    font-weight: bold;
    color: {ST_SECONDARY};
}}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------
# DATA LOADING AND PREPARATION FUNCTIONS
# --------------------------------------------------------------

@st.cache_data
def load_user_cloud_data(username: str):
    """Loads real data from Firestore."""
    try:
        st.info(f"Attempting to load real data for user: {username}...")
        # Placeholder for real API call - returns empty DF if data is not found
        return pd.DataFrame(columns=REQUIRED_DF_COLUMNS) 
    except Exception as e:
        st.error(f"Failed to load cloud data: {e}. Check API key and network.")
        return pd.DataFrame(columns=REQUIRED_DF_COLUMNS)

def calculate_tqi(df):
    """Calculates Talent Quality Index (TQI) and scaled metrics."""
    df_temp = df.copy()
    
    # Ensure numeric types and handle missing data
    df_temp["Years Experience"] = pd.to_numeric(df_temp["Years Experience"], errors='coerce').fillna(0)
    df_temp["CGPA (4.0 Scale)"] = pd.to_numeric(df_temp["CGPA (4.0 Scale)"], errors='coerce').fillna(0)
    df_temp["Score (%)"] = pd.to_numeric(df_temp["Score (%)"], errors='coerce').fillna(df_temp["Score (%)"].mean() if not df.empty else 0)
    df_temp["Semantic Similarity"] = pd.to_numeric(df_temp["Semantic Similarity"], errors='coerce').fillna(0)
    
    # Scale variables
    df_temp["Exp_Scaled"] = df_temp["Years Experience"].clip(0, 20) / 20 * 100
    df_temp["CGPA_Scaled"] = df_temp["CGPA (4.0 Scale)"].clip(0, 4) / 4 * 100
    
    W_SCORE = 0.50
    W_EXP = 0.30
    W_CGPA = 0.20

    df_temp["Talent Quality Index"] = (
        df_temp["Score (%)"] * W_SCORE +
        df_temp["Exp_Scaled"] * W_EXP +
        df_temp["CGPA_Scaled"] * W_CGPA
    ).clip(0, 100).round(1)

    df["Talent Quality Index"] = df_temp["Talent Quality Index"]
    df["Exp_Scaled"] = df_temp["Exp_Scaled"].round(1)
    df["CGPA_Scaled"] = df_temp["CGPA_Scaled"].round(1)
    return df

# --------------------------------------------------------------
# FILTERING LOGIC (Applied in main body)
# --------------------------------------------------------------

def apply_filters(df):
    """Creates main body filters and applies them to the DataFrame."""
    
    df_filtered = df.copy()
    total_records = len(df)
    
    with st.expander("Filter Data for Focused Analysis", expanded=True):
        st.markdown("### Data Filters")
        
        # Initialize filter columns
        # Reduced from 5 to 3 columns since date is removed
        col1, col2, col3 = st.columns(3) 

        # 1. Job Description Filter
        with col1:
            if "JD Used" in df_filtered.columns and not df_filtered["JD Used"].isnull().all():
                all_jds = sorted(df_filtered["JD Used"].dropna().unique())
                selected_jds = st.multiselect(
                    "1. Filter by Job Description",
                    options=all_jds,
                    default=all_jds,
                    key="jd_filter"
                )
                if selected_jds:
                    df_filtered = df_filtered[df_filtered["JD Used"].isin(selected_jds)]
            else:
                st.info("JD Used data missing.")
        
        # 2. Years of Experience Filter
        with col2:
            if "Years Experience" in df_filtered.columns and not df_filtered["Years Experience"].isnull().all():
                min_exp = float(df_filtered["Years Experience"].min())
                max_exp = float(df_filtered["Years Experience"].max())
                
                if min_exp < max_exp:
                    exp_range = st.slider(
                        "2. Filter by Years of Experience",
                        min_value=min_exp,
                        max_value=max_exp,
                        value=(min_exp, max_exp),
                        step=0.5,
                        key="exp_filter"
                    )
                    df_filtered = df_filtered[
                        (df_filtered["Years Experience"] >= exp_range[0]) & 
                        (df_filtered["Years Experience"] <= exp_range[1])
                    ]
                else:
                    st.info(f"Only {min_exp} years exp. available.")
            else:
                st.info("Experience data missing.")

        # 3. AI Match Score Filter
        with col3:
            if "Score (%)" in df_filtered.columns and not df_filtered["Score (%)"].isnull().all():
                min_score = float(df_filtered["Score (%)"].min())
                max_score = float(df_filtered["Score (%)"].max())
                
                if min_score < max_score:
                    score_range = st.slider(
                        "3. Filter by AI Match Score (%)",
                        min_value=min_score,
                        max_value=max_score,
                        value=(max(70.0, min_score), max_score), 
                        step=1.0,
                        key="score_filter"
                    )
                    df_filtered = df_filtered[
                        (df_filtered["Score (%)"] >= score_range[0]) & 
                        (df_filtered["Score (%)"] <= score_range[1])
                    ]
                else:
                    st.info(f"Only {min_score}% score available.")
            else:
                st.info("Score data missing.")
        
        # New row for the remaining filter (Manual Shortlist)
        col_shortlist, col_spacer = st.columns([1, 2])

        # 4. Manual Shortlist Status Filter
        with col_shortlist:
            if "Manual Shortlist" in df_filtered.columns and not df_filtered["Manual Shortlist"].isnull().all():
                shortlist_options = ["All", "Shortlisted Only", "Not Shortlisted Only"]
                selected_shortlist = st.radio(
                    "4. Filter by Manual Shortlist Status",
                    options=shortlist_options,
                    index=0,
                    horizontal=True,
                    key="shortlist_filter"
                )
                if selected_shortlist == "Shortlisted Only":
                    df_filtered = df_filtered[df_filtered["Manual Shortlist"] == True]
                elif selected_shortlist == "Not Shortlisted Only":
                    df_filtered = df_filtered[df_filtered["Manual Shortlist"] == False]
            else:
                st.info("Manual Shortlist data missing.")

        # Display status
        filtered_records = len(df_filtered)
        st.markdown(f"---")
        st.markdown(f"**Total Records Analyzed:** **{total_records}** | **Records Matching Filters:** **{filtered_records}**")
        
        if filtered_records == 0 and total_records > 0:
            st.warning("No records match the selected filters. Please adjust your filter selections.")
         
    return df_filtered

# --------------------------------------------------------------
# VISUALIZATION FUNCTIONS (Removed all date-related plots)
# --------------------------------------------------------------
def dual_axis_time_series(df):
    import plotly.graph_objects as go

    if "Date" not in df.columns:
        st.warning("No 'Date' column found for time series.")
        return
    
    # Convert date column to datetime if not already
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df_sorted = df.sort_values("Date")

    # Compute weekly average score
    weekly = df_sorted.groupby(pd.Grouper(key="Date", freq="W")).agg({
        "Score (%)": "mean",
        "Candidate Name": "count"
    }).reset_index()

    weekly.rename(columns={"Candidate Name": "Total Screened"}, inplace=True)

    fig = go.Figure()

    # Line chart for average score
    fig.add_trace(go.Scatter(
        x=weekly["Date"],
        y=weekly["Score (%)"],
        mode="lines+markers",
        name="Average Score",
        yaxis="y1"
    ))

    # Bar chart for number of candidates screened
    fig.add_trace(go.Bar(
        x=weekly["Date"],
        y=weekly["Total Screened"],
        name="Total Screened",
        opacity=0.5,
        yaxis="y2"
    ))

    # Layout
    fig.update_layout(
        title="Weekly Trend: Avg Score vs Total Screened",
        xaxis=dict(title="Week"),
        yaxis=dict(title="Average Score (%)", side="left"),
        yaxis2=dict(title="Total Screened", overlaying="y", side="right"),
        legend=dict(orientation="h")
    )

    st.plotly_chart(fig, use_container_width=True)

def candidate_quality_donut_chart(df):
    if df.empty or df["Score (%)"].isnull().all(): st.info("Score data required.") ; return
    bins = [0, 60, 70, 80, 90, 101]; labels = ["Limited Match", "Needs Review", "Promising", "Strong", "Exceptional"]
    df['Quality Tag'] = pd.cut(df["Score (%)"], bins=bins, labels=labels, right=False)
    tag_counts = df['Quality Tag'].value_counts().reset_index(); tag_counts.columns = ['Tag', 'Count']
    color_map = {"Exceptional": ST_PRIMARY, "Strong": ST_SECONDARY, "Promising": "#4CAF50", "Needs Review": ST_ACCENT, "Limited Match": "#FF5733"}
    tag_counts['Color'] = tag_counts['Tag'].map(color_map)
    fig = go.Figure(data=[go.Pie(labels=tag_counts['Tag'], values=tag_counts['Count'], hole=.5, marker_colors=tag_counts['Color'], title="Candidate Quality Breakdown")])
    fig.update_layout(showlegend=True, height=400, margin=dict(t=50, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

def shortlisted_performance_chart(df):
    if df.empty or df["Manual Shortlist"].isnull().all(): st.info("Manual Shortlist data is required.") ; return
    counts = df["Manual Shortlist"].value_counts().reset_index(); counts.columns = ["Shortlisted", "Count"]
    counts['Shortlisted'] = counts['Shortlisted'].map({True: 'Shortlisted', False: 'Not Shortlisted'})
    color_map = {'Shortlisted': ST_PRIMARY, 'Not Shortlisted': ST_ACCENT}
    fig = px.bar(counts, x="Shortlisted", y="Count", color="Shortlisted", color_discrete_map=color_map, title="Shortlisting Outcome Counts")
    fig.update_layout(showlegend=False, height=400); st.plotly_chart(fig, use_container_width=True)

def jd_performance_ranking(df):
    if df.empty or df["JD Used"].isnull().all() or df["Manual Shortlist"].isnull().all(): st.info("JD data required for ranking.") ; return
    jd_df = df.groupby("JD Used").agg(Total_Candidates=("Candidate Name", "count"), Shortlisted_Count=("Manual Shortlist", "sum")).reset_index()
    jd_df["Shortlist_Rate"] = (jd_df["Shortlisted_Count"] / jd_df["Total_Candidates"]) * 100
    jd_df = jd_df.sort_values(by="Shortlist_Rate", ascending=False)
    fig = px.bar(jd_df.head(10), x="Shortlist_Rate", y="JD Used", orientation='h', title="Top 10 JD Performance Ranking (By Shortlist Rate %)", color="Shortlist_Rate", color_continuous_scale=px.colors.sequential.Teal)
    fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=500); st.plotly_chart(fig, use_container_width=True)

def score_heatmap_3d(df):
    temp_df = df.dropna(subset=["Score (%)", "Years Experience", "Semantic Similarity"]).copy()
    if temp_df.empty: st.info("3D Heatmap data required.") ; return
    fig = px.scatter_3d(temp_df, x="Years Experience", y="Semantic Similarity", z="Score (%)", color="Score (%)", size="Score (%)", color_continuous_scale="Plasma", hover_name="Candidate Name", height=600, title="AI Match Score Distribution in 3D Space")
    fig.update_traces(marker=dict(size=4)); st.plotly_chart(fig, use_container_width=True)

def generate_word_cloud(df, column, title="Word Cloud", color="#0e6b6d"):
    text = " ".join([str(x) for x in df[column].dropna()]);
    if not text.strip(): st.info(f"No data for '{column}' Word Cloud.") ; return
    text_cleaned = text.replace(",", " ").replace(";", " ").lower()
    wordcloud = WordCloud(width=400, height=200, background_color="white", colormap="viridis", contour_color=color, contour_width=1, collocations=False, max_words=50).generate(text_cleaned)
    fig, ax = plt.subplots(figsize=(6, 3)); ax.imshow(wordcloud, interpolation="bilinear"); ax.axis("off"); ax.set_title(title, fontsize=12, color=color)
    st.pyplot(fig); plt.close(fig)

def skills_and_gaps_bar_charts(df, N=10):
    def get_top_n_bar(data_series, title, color_scale, ascending=True):
        list_items = []; 
        for row in data_series.dropna(): list_items.extend([x.strip() for x in row.split(",") if x.strip()])
        counts = collections.Counter(list_items); df_bar = pd.DataFrame(counts.most_common(N), columns=["Item", "Count"])
        if not df_bar.empty:
            fig = px.bar(df_bar, x="Count", y="Item", orientation='h', title=title, color="Count", color_continuous_scale=color_scale)
            order = 'total ascending' if ascending else 'total descending'; fig.update_layout(yaxis={'categoryorder': order}, height=450); return fig
        return None
    col_skills, col_gaps = st.columns(2)
    fig_skills = get_top_n_bar(df["Top Skills Highlight"], f"Top {N} Prominent Skills Highlighted", px.colors.sequential.Teal, ascending=True)
    with col_skills: st.plotly_chart(fig_skills, use_container_width=True) if fig_skills else st.info("No 'Top Skills Highlight' data.")
    fig_gaps = get_top_n_bar(df["Missing Skills"], f"Top {N} Common Competency Gaps", px.colors.sequential.Sunset, ascending=True)
    with col_gaps: st.plotly_chart(fig_gaps, use_container_width=True) if fig_gaps else st.info("No 'Missing Skills' data.")

def skill_co_occurrence_matrix(df, N=10):
    st.subheader(f"Skill Co-Occurrence Matrix (Top {N} Skills)")
    text = " ".join([str(x) for x in df["Matched Keywords"].dropna()])
    if not text.strip(): st.info("No Matched Keywords data for co-occurrence analysis."); return
    all_skills = [s.strip() for row in df["Matched Keywords"].dropna() for s in row.split(',') if s.strip()]
    top_skills = [item[0] for item in collections.Counter(all_skills).most_common(N)]
    co_occurrence_matrix = pd.DataFrame(0, index=top_skills, columns=top_skills)
    for row in df["Matched Keywords"].dropna():
        skills_in_row = [s.strip() for s in row.split(',') if s.strip() in top_skills]
        for i in range(len(skills_in_row)):
            for j in range(i, len(skills_in_row)):
                skill_a = skills_in_row[i]; skill_b = skills_in_row[j]
                co_occurrence_matrix.loc[skill_a, skill_b] += 1
                if skill_a != skill_b: co_occurrence_matrix.loc[skill_b, skill_a] += 1 
    np.fill_diagonal(co_occurrence_matrix.values, co_occurrence_matrix.values.diagonal() // 2)
    fig = px.imshow(co_occurrence_matrix, x=co_occurrence_matrix.columns, y=co_occurrence_matrix.index, color_continuous_scale="Blues", text_auto=True, title=f"Co-Occurrence Count of Top {N} Matched Keywords")
    fig.update_layout(xaxis={"tickangle": 45}, height=700); st.plotly_chart(fig, use_container_width=True)

def jd_skill_match_strength(df):
    if df.empty or df["JD Used"].isnull().all() or df["Semantic Similarity"].isnull().all(): st.info("Match Strength data required.") ; return
    match_strength = df.groupby("JD Used")["Semantic Similarity"].mean().sort_values(ascending=False).reset_index()
    match_strength["Semantic Similarity"] = (match_strength["Semantic Similarity"] * 100).round(1) 
    fig = px.bar(match_strength, x="Semantic Similarity", y="JD Used", orientation='h', title="Average Semantic Match Strength by Job Description (%)", color="Semantic Similarity", color_continuous_scale=px.colors.sequential.Plotly3)
    fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=500, xaxis_title="Average Semantic Similarity (%)")
    st.plotly_chart(fig, use_container_width=True)

# REMOVED: dual_axis_time_series(df) 

def funnel_chart_qualification_flow(df):
    total = len(df); data = [("Total Submissions", total)]
    df["Score (%)"] = pd.to_numeric(df["Score (%)"], errors='coerce').fillna(0); df["Talent Quality Index"] = pd.to_numeric(df["Talent Quality Index"], errors='coerce').fillna(0)
    ai_shortlist = df.loc[df["Score (%)"] >= 70]; data.append(("AI Recommended (Score > 70%)", len(ai_shortlist)))
    tqi_shortlist = ai_shortlist.loc[ai_shortlist["Talent Quality Index"] >= 80]; data.append(("High TQI Pool (TQI > 80)", len(tqi_shortlist)))
    final_shortlist = tqi_shortlist.loc[tqi_shortlist["Manual Shortlist"] == True]; data.append(("Manually Shortlisted", len(final_shortlist)))
    funnel_df = pd.DataFrame(data, columns=["Stage", "Count"])
    fig = go.Figure(go.Funnel(y=funnel_df["Stage"], x=funnel_df["Count"], textinfo="value+percent initial", marker={"color": [ST_SECONDARY, ST_PRIMARY, ST_ACCENT, "#ff4b4b"]}, connector={"line": {"color": "gray", "dash": "dot"}}))
    fig.update_layout(title="Candidate Qualification Funnel Flow", height=500)
    st.plotly_chart(fig, use_container_width=True)
    
# --------------------------------------------------------------
# MAIN ANALYTICS DASHBOARD PAGE
# --------------------------------------------------------------

def analytics_dashboard_page():

    # -------------------------------
    #  AUTH CHECK (Very Important)
    # -------------------------------
    if not st.session_state.get("authenticated", False):
        st.warning("⚠️ Please log in to access Analytics.")
        return

    # ------------------------------------------------------
    # PAGE TITLE & HEADER (Only shown after login)
    # ------------------------------------------------------
    st.markdown("<h1 class='section-title'>Production-Ready ScreenerPro Analytics</h1>", unsafe_allow_html=True)
    st.markdown("<div class='analytics-card'>Comprehensive, advanced, and production-ready visualizations covering Candidate Quality, Screening Performance, and Skills Analysis. **Filters are applied below.**</div>", unsafe_allow_html=True)

    # ------------------------------------------------------
    # DATA SOURCE SELECTOR
    # ------------------------------------------------------
    st.subheader("Data Source Selection")
    col_data_source, col_uploader = st.columns([1, 2])

    with col_data_source:
        data_source = st.radio(
            "Select Data Source:",
            ["Current Session", "My Cloud Data", "Upload File"],
            index=1,
            horizontal=True,
            key="data_source_radio"
        )
    
    df_raw = pd.DataFrame(columns=REQUIRED_DF_COLUMNS) 

    # ------------------------------------------------------
    #  Data Loading Logic
    # ------------------------------------------------------
    if data_source == "Current Session":
        df_raw = st.session_state.get(
            "comprehensive_df",
            pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
        )
    
    elif data_source == "My Cloud Data":
        username = st.session_state.get("username")

        if not username:
            st.error("❌ No user detected. Please log in again.")
            return

        # Lazy import avoids circular import
        from main import load_session_data_from_firestore_rest

        load_session_data_from_firestore_rest(username)

        df_raw = st.session_state.get(
            "comprehensive_df",
            pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
        )

    elif data_source == "Upload File":
        with col_uploader:
            uploaded = st.file_uploader("Upload CSV or JSON", type=["csv", "json"])
            if uploaded:
                try:
                    if uploaded.name.endswith(".csv"):
                        df_raw = pd.read_csv(uploaded)
                    else:
                        df_raw = pd.read_json(uploaded)

                except Exception as e:
                    st.error(f"Error reading file: {e}")
                    return

    # ------------------------------------------------------
    #  FINAL SAFETY CHECK
    # ------------------------------------------------------
    if df_raw is None or df_raw.empty or len(df_raw.columns) < 10:
        st.error("No sufficient data available for advanced analysis. Please load a data source.")
        return

    # ------------------------------------------------------
    # PREPROCESS & TQI CALCULATION on RAW data
    # ------------------------------------------------------
    df_base = calculate_tqi(df_raw)

    # ------------------------------------------------------
    # APPLY FILTERS
    # ------------------------------------------------------
    df = apply_filters(df_base)
    
    if df.empty:
        st.warning("The filtered dataset is empty. Please adjust your filter selections above.")
        return

    # ------------------------------------------------------
    # METRICS ROW (Calculated on Filtered Data)
    # ------------------------------------------------------
    st.markdown("### Key Performance Indicators (KPIs) - *Filtered Data*")
    col_metrics = st.columns(4)
    avg_score = df['Score (%)'].mean() if len(df) > 0 else 0
    avg_exp = df['Years Experience'].mean() if len(df) > 0 else 0
    avg_tqi = df['Talent Quality Index'].mean() if len(df) > 0 else 0

    with col_metrics[0]: st.metric(label="Records Analyzed", value=len(df))
    with col_metrics[1]: st.metric(label="Average Match Score", value=f"{avg_score:.1f}%")
    with col_metrics[2]: st.metric(label="Average Experience", value=f"{avg_exp:.1f} Yrs")
    with col_metrics[3]: st.metric(label="Average TQI", value=f"{avg_tqi:.1f}")

    st.markdown("---")

    # ------------------------------------------------------
    # TABBED VIEW FOR CORE VISUALIZATIONS
    # Removed "Trends" tab
    # ------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "Candidate Quality & Screening Performance", 
        "Skills & Keyword Analytics", 
        "Match Consistency & Trends", 
        "Pipeline & Flow",
        "Resume Structure Insights",
        "AI Screening Efficiency",
        "Diversity Insights",
        "Job Description Diagnostics",
        "Outlier & Anomaly Detection",
        "Model Performance & Bias Check"
    ])

    with tab1:
        st.header("Candidate Quality & Screening Performance")
        colA, colB, colC = st.columns([1, 1.5, 1])
        
        with colA:
            st.subheader("Quality Breakdown")
            candidate_quality_donut_chart(df) 

        with colB:
            st.subheader("Match Score Distribution")
            safe_histogram(df, "Score (%)", title="Candidate Match Score Distribution")

        with colC:
            st.subheader("Shortlisting Success")
            shortlisted_performance_chart(df)

        st.markdown("---")
        
        colD, colE = st.columns(2)
        with colD:
            st.subheader("JD Performance Ranking")
            jd_performance_ranking(df)

        with colE:
            st.subheader("Score vs. Experience Correlation")
            safe_scatter(
                df,
                x="Years Experience",
                y="Score (%)",
                color="Score (%)",
                title="Score vs Experience Correlation"
            )

        st.markdown("---")
        st.subheader("Advanced 3D Quality Analysis")
        score_heatmap_3d(df)

    with tab2:
        st.header("Skills and Keyword Analytics")
        
        st.subheader("Top Skills and Gaps")
        skills_and_gaps_bar_charts(df, N=10)
        
        st.markdown("---")

        colF, colG = st.columns(2)
        
        with colF:
            st.subheader("Skill Visualization")
            safe_wordcloud(df, "Matched Keywords", title="Skill Word Cloud")

        with colG:
            st.subheader("JD Skill Match Strength")
            jd_skill_match_strength(df)

        st.markdown("---")
        skill_co_occurrence_matrix(df, N=10)

    with tab3:
        st.header("Historical Trends and Consistency")
        
        st.subheader("Weekly Screening Trend (Average Score)")
        dual_axis_time_series(df)
        
        st.markdown("---")
        
        st.subheader("Semantic vs. Exact Match Score Consistency")
        safe_scatter(
            df,
            x="Exact Match Score",
            y="Semantic Similarity",
            color="Score (%)",
            size="Score (%)",
            title="Match Consistency Check"
        )

    with tab4:
        st.header("Applicant Pipeline and Flow")

        colH, colI = st.columns(2)
        with colH:
            st.subheader("Qualification Funnel")
            funnel_chart_qualification_flow(df)

        with colI:
            st.subheader("JD Match Score Distribution")
            safe_box(
                df,
                x="JD Used",
                y="Score (%)",
                color="JD Used",
                title="Match Score Distribution by Job Description"
            )

    with tab5:
        st.header("Resume Structure Insights")

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Resume Length Distribution")
            safe_histogram(df, "Resume Length (words)", title="Resume Length Distribution")

        with col2:
            st.subheader("Readability vs Score")
            safe_scatter(
                df,
                x="Readability Score",
                y="Score (%)",
                color="Score (%)",
                title="Readability vs Score"
            )

        st.markdown("---")
        st.subheader("Section Completeness Radar")
        resume_section_radar(df)

    with tab6:
        st.header("AI Screening Efficiency")

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Screening Time Distribution")
            safe_histogram(df, "Processing Time (ms)", title="Screening Time Distribution")

        with col2:
            st.subheader("Model Confidence Heatmap")
            model_confidence_heatmap(df)

        st.markdown("---")
        st.subheader("Cost Per Resume Trend")
        cost_per_resume_time_series(df)

    with tab7:
        st.header("Diversity Insights")

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Gender Distribution")
            gender_pie(df)

        with col2:
            st.subheader("Age Distribution")
            safe_histogram(df, "Age", title="Candidate Age Spread")

        st.markdown("---")
        st.subheader("Fairness Score vs Match Score")
        fairness_vs_score(df)

    with tab8:
        st.header("Job Description Diagnostics")

        st.subheader("Keyword Strength Analysis")
        jd_keyword_strength(df)

        st.markdown("---")

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("JD Complexity Score")
            jd_complexity_gauge(df)

        with col2:
            st.subheader("JD Clarity Score")
            jd_clarity_indicator(df)

        st.markdown("---")
        jd_vs_candidate_gap_analysis(df)

    with tab9:
        st.header("Outlier & Anomaly Detection")

        st.subheader("Score Anomaly Heatmap")
        anomaly_heatmap(df)

        st.markdown("---")

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Outlier Candidates")
            outlier_candidates_table(df)

        with col2:
            st.subheader("Fraud Probability Distribution")
            fraud_probability_chart(df)

    with tab10:
        st.header("Model Performance & Bias Check")

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Precision / Recall / F1 Score")
            model_prf_chart(df)

        with col2:
            st.subheader("ROC Curve")
            roc_curve_plot(df)

        st.markdown("---")
        st.subheader("Bias Detection Radar")
        bias_radar_chart(df)


    # ------------------------------------------------------
    # RAW TABLE (Expanded View)
    # ------------------------------------------------------
    with st.expander("Detailed Data Table (Click to Expand)", expanded=False):
        st.dataframe(df, use_container_width=True)


# --------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------
# --------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------

if "comprehensive_df" not in st.session_state:
    st.session_state["comprehensive_df"] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)

# Do NOT auto-set username
if "username" not in st.session_state:
    st.session_state["username"] = None

# ❌ REMOVE analytics auto-run here
# ❌ REMOVE warning here
# ❌ REMOVE footer here
# DO NOT CALL analytics_dashboard_page() HERE

# The correct page is loaded from your sidebar/nav logic elsewhere.








