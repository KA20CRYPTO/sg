import streamlit as st
import requests
import streamlit.components.v1 as components
import json
import urllib.parse
from firebase_config import (
    FIRESTORE_DOCUMENTS_URL,
    FIREBASE_WEB_API_KEY,
)

# =========================================================
# CONFIG & SETTINGS
# =========================================================
PROJECT_ID = FIRESTORE_DOCUMENTS_URL.split("/projects/")[1].split("/")[0]

st.set_page_config(
    page_title="ScreenerPro Blog | AI Hiring Insights",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# BEAUTIFUL UI & CSS (Aligned with main.py)
# =========================================================
def load_css(css_file):
    try:
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        pass

# Load master styles
load_css("style.css")

st.markdown("""
<style>
    /* HIDE DEFAULT STREAMLIT NAVIGATION & HEADER */
    [data-testid="stSidebarNav"] {display: none !important;}
    [data-testid="stHeader"] {display: none !important;}
    #MainMenu {display: none !important;}
    footer {visibility: hidden !important;}

    /* BLOG SPECIFIC OVERRIDES */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        max-width: 1200px;
    }

    /* BLOG CARD DESIGN */
    .blog-card {
        border-radius: 20px;
        background: white;
        border: 1px solid #e2e8f0;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 2rem;
        cursor: pointer;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .blog-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
        border-color: #00cec9;
    }
    .blog-card img {
        width: 100%;
        height: 240px;
        object-fit: cover;
    }
    .blog-tag {
        background: #e0fcfb;
        color: #00cec9 !important;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 0.75rem;
    }
    .blog-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0f172a !important; /* Matches Slate-900 */
        margin-bottom: 0.75rem;
        line-height: 1.3;
    }
    .blog-desc {
        color: #64748b !important; /* Matches Slate-500 */
        font-size: 1rem;
        line-height: 1.6;
        height: 4.8rem;
        overflow: hidden;
    }
    
    /* DETAIL VIEW */
    .detail-container h1 {
        font-size: 3.5rem !important;
        font-weight: 900 !important;
        background: linear-gradient(90deg, #2563eb, #0ea5e9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem !important;
    }
    .author-badge {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 2rem;
    }
    
    /* SEARCH SYNC WITH style.css input rules */
    .stTextInput > div > div > input {
        border-radius: 20px !important;
    }

    /* FORCE RADIO BUTTONS TO HIDE CIRCLES (MATCH main.py) */
    .stSidebar .stRadio div[role="radiogroup"] label span:first-child {
        display: none !important;
    }
    .stSidebar .stRadio div[role="radiogroup"] label {
        margin-bottom: 5px !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# FIRESTORE UTILS
# =========================================================

@st.cache_data(ttl=600)
def from_firestore_format(doc: dict) -> dict:
    res = {"id": doc["name"].split("/")[-1]}
    fields = doc.get("fields", {})
    for k, v in fields.items():
        if "stringValue" in v:
            res[k] = v["stringValue"]
        elif "integerValue" in v:
            res[k] = int(v["integerValue"])
        elif "booleanValue" in v:
            res[k] = v["booleanValue"]
        elif "mapValue" in v:
            res[k] = from_firestore_format({"name": "", "fields": v["mapValue"].get("fields", {})})
        elif "arrayValue" in v:
            res[k] = [val.get("stringValue", "") for val in v["arrayValue"].get("values", [])]
    return res

def fetch_published_blogs():
    url = f"{FIRESTORE_DOCUMENTS_URL}/blogs?key={FIREBASE_WEB_API_KEY}"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            blogs = []
            if "documents" in data:
                for doc in data["documents"]:
                    b = from_firestore_format(doc)
                    if b.get("status") == "published":
                        blogs.append(b)
            return sorted(blogs, key=lambda x: x.get("published_at", ""), reverse=True)
    except Exception as e:
        st.error(f"Error: {e}")
    return []

def increment_view(doc_id, current_views):
    url = f"{FIRESTORE_DOCUMENTS_URL}/blogs/{doc_id}?updateMask.fieldPaths=analytics.views&key={FIREBASE_WEB_API_KEY}"
    payload = {"fields": {"analytics": {"mapValue": {"fields": {"views": {"integerValue": str(current_views + 1)}}}}}}
    requests.patch(url, json=payload)

# =========================================================
# SEO INJECTION
# =========================================================

def set_blog_seo(blog):
    seo = blog.get("seo", {})
    title = seo.get("meta_title", blog.get("title", "ScreenerPro Blog"))
    desc = seo.get("meta_description", "")
    keywords = ", ".join(seo.get("keywords", []))
    
    meta_html = f"""
    <script>
        window.parent.document.title = "{title}";
        const head = window.parent.document.getElementsByTagName('head')[0];
        const updateMeta = (name, content, attr='name') => {{
            let meta = window.parent.document.querySelector(`meta[${{attr}}="${{name}}"]`);
            if (!meta) {{ meta = window.parent.document.createElement('meta'); meta.setAttribute(attr, name); head.appendChild(meta); }}
            meta.content = content;
        }};
        updateMeta('description', "{desc}");
        updateMeta('keywords', "{keywords}");
        updateMeta('og:title', "{title}", 'property');
        updateMeta('og:description', "{desc}", 'property');
        if ("{blog.get('cover_image_url', '')}") updateMeta('og:image', "{blog.get('cover_image_url', '')}", 'property');
    </script>
    """
    components.html(meta_html, height=0)

# =========================================================
# SIDEBAR CUSTOMIZATION
# =========================================================

def render_custom_sidebar(blogs):
    with st.sidebar:
        # Standard Branding
        st.image("https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhq_OCSv-QmuBjXeRQXr60EfsvVA4chRPCNslo3NhjVQkoKjUtiRfTPpGoQjyQXS7sMsJifQC6Yq34cAhNbq9lMwBXZqIIbCij1adyXSuNoyxuzOTDfrPU2dnna0baimldd7Y1KCkvaAfrWC1yLGxp25SJ9s4exJ-JAc8kNcTyUSgkLWbW2DdvhpWH4GlO/s578/logo.png", width=150)
        st.title("🧠 ScreenerPro")
        
        # Logged Out Navigation (Matches main.py)
        nav_options = [
            "Home",
            "Login / Register",
            "Public Job Board",
            "Blogs", # This is the Blogs page
            "Certificate Verification",
            "Our Clients",
            "Partner With Us",
            "Privacy Policy & Terms",
            "Feedback & Help"
        ]
        
        selected = st.radio(
            "📍 Select Page",
            nav_options,
            index=nav_options.index("Blogs")
        )
        
        # Handle Navigation Switch
        if selected != "Blogs":
            if selected == "Home":
                # landing.py is usually the entry script
                try:
                    st.switch_page("landing.py")
                except:
                    # Fallback if landing.py isn't the entry or path differs
                    st.switch_page("main.py") 
            elif selected == "Public Job Board":
                st.switch_page("pages/Public_Job_Board.py")
            elif selected == "Login / Register":
                st.session_state.current_page = "Login / Register"
                st.switch_page("pages/main.py")
            else:
                # All other pages (Our Clients, Partners, etc.) are handled inside main.py
                st.session_state.current_page = selected
                st.switch_page("pages/main.py")
            st.rerun()

        st.markdown("---")
        st.markdown("### 🔎 Search Insights")
        search_query = st.text_input("", placeholder="Type here...", label_visibility="collapsed")
        
    return search_query

def render_share_buttons(blog):
    """Renders styled social sharing buttons."""
    blog_url = f"https://screenerpro.streamlit.app?page=blog&blog={blog['slug']}"
    share_text = f"Check out this insightful article from ScreenerPro: {blog['title']}"
    
    encoded_text = urllib.parse.quote(share_text)
    encoded_url = urllib.parse.quote(blog_url)
    
    st.markdown("### 📢 Share this article")
    
    # Define sharing links
    linkedin_url = f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}"
    twitter_url = f"https://twitter.com/intent/tweet?text={encoded_text}&url={encoded_url}"
    whatsapp_url = f"https://wa.me/?text={encoded_text}%20{encoded_url}"
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown(f'<a href="{linkedin_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#0a66c2; color:white; padding:10px; border-radius:8px; text-align:center; font-weight:bold; display:flex; align-items:center; justify-content:center; gap:8px;"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16"><path d="M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 14.854V1.146zm4.943 12.248V6.169H2.542v7.225h2.401zm-1.2-8.212c.837 0 1.358-.554 1.358-1.248-.015-.709-.52-1.248-1.342-1.248-.822 0-1.359.54-1.359 1.248 0 .694.521 1.248 1.327 1.248h.016zm4.908 8.212V9.359c0-.216.016-.432.08-.586.173-.431.568-.878 1.232-.878.869 0 1.216.662 1.216 1.634v3.865h2.401V9.25c0-2.22-1.184-3.252-2.764-3.252-1.274 0-1.845.7-2.165 1.193v.025h-.016a5.54 5.54 0 0 1 .016-.025V6.169h-2.4c.03.678 0 7.225 0 7.225h2.4z"/></svg> LinkedIn</div></a>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'<a href="{twitter_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#000000; color:white; padding:10px; border-radius:8px; text-align:center; font-weight:bold; display:flex; align-items:center; justify-content:center; gap:8px;"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16"><path d="M12.6.75h2.454l-5.36 6.142L16 15.25h-4.937l-3.867-5.055-4.425 5.055H.316l5.733-6.555L0 .75h5.063l3.495 4.575L12.6.75zm-.86 13.028h1.36L4.323 2.145H2.865z"/></svg> Tweet</div></a>', unsafe_allow_html=True)
        
    with col3:
        st.markdown(f'<a href="{whatsapp_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366; color:white; padding:10px; border-radius:8px; text-align:center; font-weight:bold; display:flex; align-items:center; justify-content:center; gap:8px;"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16"><path d="M13.601 2.326A7.854 7.854 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.933 7.933 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.898 7.898 0 0 0 13.6 2.326zM7.994 14.521a6.573 6.573 0 0 1-3.356-.92l-.24-.144-2.494.654.666-2.433-.156-.251a6.56 6.56 0 0 1-1.007-3.505c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.557 6.557 0 0 1 1.928 4.66c-.004 3.639-2.961 6.592-6.592 6.592zm3.615-4.934c-.197-.099-1.17-.578-1.353-.646-.182-.065-.315-.099-.445.099-.133.197-.513.646-.627.775-.114.133-.232.148-.43.05-.197-.1-.836-.308-1.592-.985-.59-.525-.985-1.175-1.103-1.372-.114-.198-.011-.304.088-.403.087-.088.197-.232.296-.346.1-.114.133-.198.198-.33.065-.134.034-.248-.015-.347-.05-.099-.445-1.076-.612-1.47-.16-.389-.323-.335-.445-.34-.114-.007-.247-.007-.38-.007a.729.729 0 0 0-.529.247c-.182.198-.691.677-.691 1.654 0 .977.71 1.916.81 2.049.098.133 1.394 2.132 3.383 2.992.47.205.84.326 1.129.418.475.152.904.129 1.246.08.38-.058 1.171-.48 1.338-.943.164-.464.164-.86.114-.943-.049-.084-.182-.133-.38-.232z"/></svg> WhatsApp</div></a>', unsafe_allow_html=True)

# =========================================================
# UI RENDERS
# =========================================================

def render_listing(all_blogs, search_query):
    # Filter blogs if search is active
    blogs = all_blogs
    if search_query:
        blogs = [b for b in all_blogs if search_query.lower() in b['title'].lower() or search_query.lower() in b.get('content', '').lower()]

    st.markdown("<h1 style='text-align: center; color: #1e3a8a; font-size: 4rem; font-weight: 900; margin-bottom: 0.5rem;'>The Intelligence Hub</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.4rem; font-weight: 500;'>Expert insights on AI recruitment, talent strategy, and the future of work.</p>", unsafe_allow_html=True)
    st.write("")
    st.write("")
    st.write("")

    if not blogs:
        st.info("No articles found matching your criteria.")
        return

    # Featured Post (if no search)
    if not search_query and len(blogs) > 0:
        featured = blogs[0]
        col1, col2 = st.columns([1.5, 1])
        with col1:
            img_url = featured.get('cover_image_url', '')
            if img_url:
                st.image(img_url, use_container_width=True)
            else:
                st.info("No cover image available")
        with col2:
            st.markdown(f"<span class='blog-tag'>FEATURED POST</span>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='color: #1e3a8a; font-size: 2.5rem; font-weight: 900; margin-bottom: 1rem;'>{featured['title']}</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: #64748b; font-size: 1.2rem; line-height: 1.6; margin-bottom: 2rem;'>{featured.get('seo', {}).get('meta_description', '')}</p>", unsafe_allow_html=True)
            if st.button("Read Featured Article", key="btn_featured", type="primary"):
                st.query_params["blog"] = featured["slug"]
                st.rerun()
        st.write("---")
        st.write("")

    display_blogs = blogs[1:] if not search_query and len(blogs) > 1 else blogs
    cols = st.columns(2)
    for i, b in enumerate(display_blogs):
        with cols[i % 2]:
            img_url = b.get('cover_image_url', '')
            img_html = f'<img src="{img_url}">' if img_url else '<div style="height:240px; background:#f1f5f9; display:flex; align-items:center; justify-content:center; color:#cbd5e1;">No Image</div>'
            st.markdown(f"""
            <div class="blog-card">
                {img_html}
                <div class="blog-content">
                    <span class="blog-tag">AI HIRING</span>
                    <div class="blog-title">{b['title']}</div>
                    <div class="blog-desc">{b.get('seo', {}).get('meta_description', '')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
            if st.button(f"Dive In →", key=f"btn_{b['slug']}", use_container_width=True):
                st.query_params["blog"] = b["slug"]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("")

def render_detail(slug, all_blogs):
    blog = next((b for b in all_blogs if b['slug'] == slug), None)
    if not blog:
        st.error("Post not found.")
        if st.button("⬅ Back to Feed"):
            st.query_params.clear()
            st.rerun()
        return

    set_blog_seo(blog)
    
    if f"v_{blog['id']}" not in st.session_state:
        increment_view(blog["id"], blog.get("analytics", {}).get("views", 0))
        st.session_state[f"v_{blog['id']}"] = True

    # Detail View
    if st.button("⬅ Back to Feed"):
        st.query_params.clear()
        st.rerun()
    
    img_url = blog.get('cover_image_url', '')
    if img_url:
        st.image(img_url, use_container_width=True)
    
    st.markdown(f"<h1 style='color: #222; font-size: 3.5rem; font-weight: 800; line-height: 1.1; margin-top: 1.5rem;'>{blog['title']}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        <div class="author-badge">
            <div style="width: 50px; height: 50px; background: #e2e8f0; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #1e3a8a;">SP</div>
            <div>
                <div style="font-weight: 700; color: #1e3a8a;">ScreenerPro Editorial</div>
                <div style="font-size: 0.85rem; color: #64748b;">{blog.get('published_at', '')[:10]} • {blog.get('analytics', {}).get('views', 0) + 1} Reads</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("---")
    st.markdown(f"<div style='font-size: 1.25rem; line-height: 1.8; color: #0f172a;'>{blog.get('content', '')}</div>", unsafe_allow_html=True)
    st.write("---")
    
    # Share Buttons
    render_share_buttons(blog)
    st.write("---")

# =========================================================
# MAIN APP
# =========================================================

def main():
    all_blogs = fetch_published_blogs()
    search_query = render_custom_sidebar(all_blogs)
    
    blog_slug = st.query_params.get("blog")
    
    if blog_slug:
        render_detail(blog_slug, all_blogs)
    else:
        render_listing(all_blogs, search_query)

if __name__ == "__main__":
    main()
