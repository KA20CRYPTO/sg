import streamlit as st
import json
import os

# --- Styling ---
st.markdown("""
<style>
/* Container */
.notes-container {
    padding: 2rem;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    animation: fadeInSlide 0.6s ease-in-out;
    font-family: 'Inter', sans-serif;
}

/* Individual note box */
.note-box {
    background: rgba(240, 249, 255, 0.3);
    border-left: 6px solid #00cec9;
    padding: 1.2rem;
    margin-bottom: 1.2rem;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.note-box:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

/* Buttons */
div.stButton > button {
    background: linear-gradient(90deg, #00bcd4, #00cec9);
    color: white;
    border-radius: 12px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 15px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
div.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.25);
    background: linear-gradient(90deg, #00cec9, #00bcd4);
}

/* Textarea & input styling */
textarea, input[type=text] {
    border-radius: 12px;
    border: 2px solid #00bcd4;
    padding: 10px;
    font-size: 16px;
    width: 100%;
    transition: all 0.3s ease;
}
textarea:focus, input[type=text]:focus {
    border-color: #00cec9;
    box-shadow: 0 0 10px rgba(0, 206, 201, 0.4);
}

/* Fade-in animation */
@keyframes fadeInSlide {
    0% { opacity: 0; transform: translateY(20px); }
    100% { opacity: 1; transform: translateY(0); }
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="notes-container">', unsafe_allow_html=True)
st.subheader("📝 Candidate Notes")

# Load notes
notes_file = "notes.json"
if os.path.exists(notes_file):
    with open(notes_file, "r", encoding="utf-8") as f:
        notes = json.load(f)
else:
    notes = {}

candidates = sorted(notes.keys())
selected = st.selectbox("📄 Select Candidate", candidates)

if selected:
    st.markdown(f"#### 🗒️ Notes for {selected}")
    st.markdown('<div class="note-box">', unsafe_allow_html=True)
    text = st.text_area("Edit Note", value=notes[selected], height=150)
    col1, col2 = st.columns(2)
    if col1.button("💾 Save Note"):
        notes[selected] = text
        with open(notes_file, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2)
        st.success("✅ Note updated.")

    if col2.button("🗑️ Delete Note"):
        notes.pop(selected, None)
        with open(notes_file, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2)
        st.warning("🗑️ Note deleted.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()
st.markdown("### ➕ Add New Note")
st.markdown('<div class="note-box">', unsafe_allow_html=True)
new_name = st.text_input("👤 Candidate Name")
new_note = st.text_area("📝 Note", height=120)
if st.button("➕ Save New Note"):
    if new_name.strip():
        notes[new_name.strip()] = new_note.strip()
        with open(notes_file, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2)
        st.success(f"✅ Note added for {new_name.strip()}")
        st.rerun()
    else:
        st.error("❌ Candidate name cannot be empty.")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
