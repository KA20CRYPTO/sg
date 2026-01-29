import streamlit as st
import pdfplumber
import re
import pandas as pd
import io

# --- Styling ---
st.markdown("""
<style>
/* Main container */
.search-box {
    padding: 2rem;
    margin-top: 1rem;
    border-radius: 20px;
    background: rgba(255,255,255,0.12);
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.08);
    animation: slideFade 0.6s ease-in-out;
    font-family: 'Inter', sans-serif;
}

/* Result card */
.result-box {
    background: rgba(247, 250, 255, 0.3);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    border-radius: 16px;
    border-left: 6px solid #00cec9;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    animation: fadeInResult 0.6s ease;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.result-box:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.12);
}

/* Highlighted keyword */
.highlight {
    background-color: #ffeaa7;
    font-weight: 600;
    padding: 3px 7px;
    border-radius: 5px;
}

/* Upload & input styling */
input[type=file], input[type=text] {
    border-radius: 12px;
    border: 2px solid #00bcd4;
    padding: 10px;
    font-size: 16px;
    width: 100%;
    transition: all 0.3s ease;
}
input[type=text]:focus {
    border-color: #00cec9;
    box-shadow: 0 0 12px rgba(0, 206, 201, 0.4);
}

/* Download button styling */
div.stDownloadButton>button {
    background: linear-gradient(90deg, #00bcd4, #00cec9);
    color: white;
    border-radius: 12px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 15px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
div.stDownloadButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.25);
    background: linear-gradient(90deg, #00cec9, #00bcd4);
}

/* Animations */
@keyframes slideFade {
    0% { opacity: 0; transform: translateY(20px); }
    100% { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInResult {
    0% { opacity: 0; transform: scale(0.98); }
    100% { opacity: 1; transform: scale(1); }
}
</style>
""", unsafe_allow_html=True)

# --- UI Header ---
st.markdown('<div class="search-box">', unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; color:#00cec9;'>🔍 Resume Search Engine</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#555;'>Upload resumes and search for single or multiple keywords (e.g., <code>python, sql</code>).</p>", unsafe_allow_html=True)

# --- File Upload ---
resumes = st.file_uploader("📤 Upload Resumes (PDF)", type="pdf", accept_multiple_files=True, key="resume_search_upload")
resume_texts = {}

if resumes:
    st.success(f"✅ {len(resumes)} resume(s) uploaded.")
    for resume in resumes:
        try:
            with pdfplumber.open(resume) as pdf:
                text = ''.join(page.extract_text() or '' for page in pdf.pages)
                resume_texts[resume.name] = text
        except Exception as e:
            st.warning(f"⚠️ Error reading {resume.name}")

    query = st.text_input("🔎 Enter keywords (comma-separated)").strip().lower()
    download_rows = []

    if query:
        keywords = [q.strip() for q in query.split(',') if q.strip()]
        st.markdown("### 📄 Search Results")
        found = False

        for name, content in resume_texts.items():
            content_lower = content.lower()
            matched_snippets = []
            for keyword in keywords:
                if keyword in content_lower:
                    found = True
                    idx = content_lower.find(keyword)
                    snippet = content[max(0, idx - 40): idx + 160]
                    highlighted = re.sub(
                        f"({re.escape(keyword)})",
                        r"<span class='highlight'>\1</span>",
                        snippet,
                        flags=re.IGNORECASE
                    )
                    matched_snippets.append(highlighted)

            if matched_snippets:
                combined_snippet = " ... ".join(matched_snippets)
                st.markdown(f"""<div class="result-box">
                <b>📄 {name}</b><br>{combined_snippet}...
                </div>""", unsafe_allow_html=True)

                download_rows.append({
                    "File Name": name,
                    "Matched Keywords": ", ".join(keywords),
                    "Snippet": ' '.join(snippet for snippet in matched_snippets)
                })

        if not found:
            st.error("❌ No matching resumes found.")

        # --- Export Button ---
        if download_rows:
            df_download = pd.DataFrame(download_rows)
            csv_buffer = io.StringIO()
            df_download.to_csv(csv_buffer, index=False)
            st.download_button("📥 Download Matched Results (CSV)", data=csv_buffer.getvalue(), file_name="matched_resumes.csv", mime="text/csv")

else:
    st.info("📁 Please upload resume PDFs to begin searching.")

st.markdown("</div>", unsafe_allow_html=True)
