import sys
from pathlib import Path

# Dynamically bootstrap project root to sys.path to prevent ModuleNotFoundError
current_file = Path(__file__).resolve()
root_dir = current_file.parent
while root_dir.parent != root_dir:
    if (root_dir / 'src').exists() or (root_dir / 'frontend').exists():
        break
    root_dir = root_dir.parent

for p in [root_dir, root_dir / 'src']:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st
import requests
import time
import json
import re
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Indian Legal Advisor",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def clean_html(html_str: str) -> str:
    if not html_str:
        return ""
    return "\n".join([line.strip() for line in html_str.split("\n")])

def parse_legal_advice_to_sections(advice_text: str) -> dict:
    if not advice_text:
        return {}
    
    # Try parsing as JSON first
    try:
        trimmed = advice_text.strip()
        if trimmed.startswith('{') and trimmed.endswith('}'):
            parsed_json = json.loads(trimmed)
            if isinstance(parsed_json, dict):
                return parsed_json
    except Exception:
        pass

    sections = {}
    lines = advice_text.split('\n')
    current_key = None
    current_content = []
    
    for line in lines:
        stripped = line.strip()
        is_header = False
        header_name = ""
        
        if stripped.startswith('#'):
            is_header = True
            header_name = stripped.lstrip('#').strip()
            
        if is_header:
            if current_key:
                sections[current_key] = '\n'.join(current_content).strip()
            
            name_lower = header_name.lower()
            if 'analysis' in name_lower or 'finding' in name_lower:
                current_key = 'analysis'
            elif 'recommend' in name_lower or 'step' in name_lower or 'action' in name_lower:
                current_key = 'recommendations'
            else:
                current_key = re.sub(r'[^a-z0-9_]', '', name_lower.replace(' ', '_'))
                
            current_content = []
        else:
            current_content.append(line)
            
    if current_key:
        sections[current_key] = '\n'.join(current_content).strip()
        
    if not sections or not any(k in sections for k in ['analysis', 'recommendations']):
        sections['analysis'] = advice_text
        
    return sections

# Styling with modern look, Outfit Google font, and glassmorphism cards
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    /* Main container and font styling */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', sans-serif;
    }
    
    .main {
        background-color: #0b0d10;
        color: #e2e8f0;
    }
    
    /* Custom Headers */
    .title-text {
        font-weight: 800;
        background: linear-gradient(135deg, #d4af37 0%, #f3e5ab 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0px;
    }
    
    .subtitle-text {
        color: #a0aec0;
        font-size: 16px;
        text-align: center;
        margin-top: 5px;
        margin-bottom: 25px;
        font-weight: 300;
    }
    
    /* Info Card Container */
    .info-card {
        background-color: #161a23;
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        margin-bottom: 15px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .info-card:hover {
        transform: translateY(-2px);
        border-color: #d4af37;
    }
    
    /* Stats Badge */
    .metric-badge {
        background: rgba(212, 175, 55, 0.1);
        border: 1px solid rgba(212, 175, 55, 0.3);
        color: #d4af37;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 13px;
        display: inline-block;
        margin-right: 8px;
    }
    
    .risk-high {
        background: rgba(255, 75, 75, 0.1);
        border: 1px solid rgba(255, 75, 75, 0.3);
        color: #ff4b4b;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 13px;
        display: inline-block;
    }
    
    .risk-medium {
        background: rgba(255, 165, 0, 0.1);
        border: 1px solid rgba(255, 165, 0, 0.3);
        color: #ffa500;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 13px;
        display: inline-block;
    }
    
    .risk-low {
        background: rgba(0, 204, 102, 0.1);
        border: 1px solid rgba(0, 204, 102, 0.3);
        color: #00cc66;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 13px;
        display: inline-block;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        border-bottom: 2px solid #2d3748;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        background-color: transparent;
        border-radius: 8px 8px 0 0;
        font-weight: 500;
        color: #a0aec0;
        transition: color 0.2s, background-color 0.2s;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: rgba(212, 175, 55, 0.1);
        color: #d4af37 !important;
        border-bottom: 2px solid #d4af37;
    }
    
    /* Custom Risk Cards */
    .risk-card {
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    .risk-card-title {
        font-size: 11px;
        color: #a0aec0;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .risk-card-value {
        font-size: 18px;
        font-weight: 700;
        margin-top: 5px;
    }
    
    /* Timeline Visuals */
    .timeline-item {
        border-left: 2px solid #d4af37;
        padding-left: 18px;
        margin-left: 10px;
        margin-bottom: 15px;
        position: relative;
    }
    .timeline-dot {
        position: absolute;
        left: -6px;
        top: 4px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #d4af37;
        box-shadow: 0 0 8px #d4af37;
    }
    .timeline-date {
        font-size: 13px;
        font-weight: 700;
        color: #d4af37;
    }
    .timeline-event {
        font-size: 14px;
        color: #e2e8f0;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Constants
API_BASE_URL = "http://127.0.0.1:8000"
API_TIMEOUT = 600  # 10 minutes for local inference

# Session state
if "query_results" not in st.session_state:
    st.session_state.query_results = None
if "fir_results" not in st.session_state:
    st.session_state.fir_results = None
if "notice_results" not in st.session_state:
    st.session_state.notice_results = None

# Header
st.markdown("<h1 class='title-text'>⚖️ Indian Legal Advisor</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-text'>Intelligent Legal Assistant Powered by InLegalBERT + FAISS + Qwen3</p>", unsafe_allow_html=True)

# Sidebar

# Session state for auth
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; color: #d4af37;'>🔐 Secure Legal Advisor Portal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a0aec0;'>Please log in or register to access the intelligent legal assistant.</p>", unsafe_allow_html=True)
    
    login_tab, register_tab = st.tabs(["🔑 Sign In", "📝 Create Account"])
    
    with login_tab:
        st.markdown("### 🔑 Enter Credentials")
        login_user = st.text_input("Username:", key="login_username_val")
        login_pass = st.text_input("Password:", type="password", key="login_password_val")
        if st.button("Sign In", type="primary", key="login_btn_click", use_container_width=True):
            if login_user.strip() and login_pass.strip():
                try:
                    res = requests.post(
                        f"{API_BASE_URL}/api/login",
                        json={"username": login_user.strip(), "password": login_pass.strip()},
                        timeout=15
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.authenticated = True
                        st.session_state.auth_token = data.get("access_token")
                        st.session_state.username = data.get("username")
                        st.session_state.role = data.get("role")
                        st.success("Access Granted! Loading system...")
                        time.sleep(1)
                        st.rerun()
                    elif res.status_code == 401:
                        st.error("❌ Authentication Failed: Invalid credentials.")
                    else:
                        st.error(f"❌ Server Error: HTTP {res.status_code}")
                except Exception as e:
                    st.error(f"❌ Failed to reach authentication service: {e}")
            else:
                st.warning("⚠️ Username and password cannot be empty.")
                
    with register_tab:
        st.markdown("### 📝 Register New User")
        reg_user = st.text_input("Choose Username:", key="reg_username_val")
        reg_pass = st.text_input("Choose Password (min 6 chars):", type="password", key="reg_password_val")
        reg_pass_confirm = st.text_input("Confirm Password:", type="password", key="reg_password_confirm_val")
        reg_role = st.selectbox("Account Access Type:", ["User", "Admin"], key="reg_role_val")
        
        if st.button("Register Account", type="primary", key="reg_btn_click", use_container_width=True):
            if reg_user.strip() and reg_pass.strip() and reg_pass_confirm.strip():
                if reg_pass != reg_pass_confirm:
                    st.error("❌ Passwords do not match!")
                elif len(reg_pass) < 6:
                    st.error("❌ Password must be at least 6 characters.")
                else:
                    try:
                        res = requests.post(
                            f"{API_BASE_URL}/api/register",
                            json={"username": reg_user.strip(), "password": reg_pass.strip(), "role": reg_role},
                            timeout=15
                        )
                        if res.status_code == 200:
                            st.success("✅ Account registered successfully! You can now log in.")
                        else:
                            st.error(f"❌ Registration failed: {res.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"❌ Failed to reach registration service: {e}")
            else:
                st.warning("⚠️ All registration fields are required.")
else:
    def render_main_app():

        with st.sidebar:
            st.markdown("## 🧭 Navigation")
            features = [
                "💡 Legal Query Advisory",
                "📄 FIR Document Analysis",
                "🔎 Legal Notice Analysis"
            ]
            if st.session_state.role == "Admin":
                features.append("⚙️ Admin Dashboard")
                
            app_mode = st.radio(
                "Select Feature:",
                features
            )
            
            st.markdown("---")
            st.markdown(f"👤 **User:** {st.session_state.username}")
            st.markdown(f"🔑 **Role:** `{st.session_state.role}`")
            if st.button("🚪 Sign Out", type="secondary", use_container_width=True, key="logout_sidebar_btn"):
                st.session_state.authenticated = False
                st.session_state.auth_token = None
                st.session_state.username = None
                st.session_state.role = None
                st.session_state.query_results = None
                st.session_state.fir_results = None
                st.session_state.notice_results = None
                st.rerun()
            
            st.markdown("---")
            st.markdown("## 🏛️ System Overview")
            st.markdown("""
            This intelligent legal assistant employs **InLegalBERT** embeddings, a **FAISS** vector database of case precedents, and **Qwen3:8B** reasoning to deliver reference and research guides for Indian law.
            """)
            
            st.markdown("---")
            st.markdown("### 📋 Supported Legal Domains")
            domains = {
                "⚖️ Criminal Law": "IPC/BNS violations, physical offense, theft, assault",
                "👨‍👩‍👧 Family Law": "Divorce, maintenance, domestic violence, custody",
                "🏠 Property Law": "Landlord-tenant disputes, boundary issues, transfer",
                "📝 Contract Law": "Breach, service agreements, commercial pacts",
                "🛒 Consumer Law": "Deficient services, product liability, fraud"
            }
            for dom, desc in domains.items():
                st.markdown(f"**{dom}**  \n<small style='color:#718096;'>{desc}</small>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 🤖 AI Legal Assistant Status")
            st.success("🟢 Online | Ready for analysis")
            
            st.markdown("---")
            st.markdown("### 📜 Disclaimer")
            st.warning("This platform is an AI advisory tool for educational and preliminary support. It does not constitute formal legal advice. Always consult a qualified lawyer.")
        
        # Top-level Navigation
        if app_mode == "💡 Legal Query Advisory":
            st.markdown("### 📝 Describe Your Legal Issue")
            query_input = st.text_area(
                "Enter query text:",
                placeholder="E.g., 'My neighbor built a fence that encroaches onto my registered property plot. When I objected, they threatened me. What are my legal remedies?'",
                height=120,
                key="query_input_box"
            )
            
            col1, col2 = st.columns([5, 1])
            with col2:
                analyze_query_btn = st.button("🔍 Analyze Query", type="primary", use_container_width=True)
                
            if analyze_query_btn and query_input.strip():
                with st.status("🔍 Legal AI System Processing...", expanded=True) as status:
                    status.write("📝 Analyzing Query...")
                    status.write("📚 Retrieving Legal References...")
                    status.write("💡 Generating Legal Analysis...")
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.auth_token}"}
                        response = requests.post(
                            f"{API_BASE_URL}/api/analyze",
                            json={
                                "query": query_input
                            },
                            headers=headers,
                            timeout=API_TIMEOUT
                        )
                        elapsed = time.time() - start_time
                        
                        if response.status_code == 401:
                            st.session_state.authenticated = False
                            st.session_state.auth_token = None
                            st.error("Session expired. Please log in again.")
                            time.sleep(1)
                            st.rerun()
                            
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.query_results = {
                                "data": data,
                                "elapsed": elapsed
                            }
                            status.update(label="✅ Advisory Report Generated!", state="complete", expanded=False)
                        else:
                            status.update(label="❌ API Error", state="error", expanded=True)
                            st.error(f"❌ API returned status code {response.status_code}")
                            try:
                                st.write(response.json())
                            except:
                                st.write(response.text)
                    except Exception as e:
                        status.update(label="❌ Connection Failed", state="error", expanded=True)
                        st.error("❌ Connection Failed. Unable to communicate with the Legal Advisor API.")
                        st.info("Please ensure that the FastAPI backend server is running on port 8000. If you are running locally, start it with: `python src/main.py`")
        
            # Render Query Results
            if st.session_state.query_results:
                res = st.session_state.query_results["data"]
                elapsed = st.session_state.query_results["elapsed"]
                
                if res.get("status") == "error":
                    st.error(f"⚠️ Rejection: {res.get('message')}")
                else:
                    # Stats Row
                    topic_info = res.get("topic", {})
                    st.markdown(clean_html(f"""
                    <div style='margin-bottom: 15px;'>
                        <span class='metric-badge'>📌 Topic: {topic_info.get('name', 'N/A').replace('_', ' ').title()} ({topic_info.get('confidence', 0)*100:.1f}%)</span>
                        <span class='metric-badge'>📚 Cases found: {len(res.get('precedents', []))}</span>
                    </div>
                    """), unsafe_allow_html=True)
                    
                    # Sub-tabs for detailed view
                    q_tab1, q_tab2, q_tab3 = st.tabs(["💡 Legal Advice", "📖 Applicable Statutes", "📚 Similar Precedents"])
                    
                    with q_tab1:
                        st.markdown("### 💡 AI Legal Advisory Report")
                        st.markdown(res.get("legal_advice", "No advice generated."))
                        
                    with q_tab2:
                        st.markdown("### ⚖️ Applicable Statutes & Code Sections")
                        statutes = res.get("statutes", {})
                        if statutes.get("details"):
                            for statute in statutes["details"]:
                                section_name = statute.get('code') or statute.get('section') or 'Section'
                                title = statute.get('title') or 'Statutory Provision'
                                desc = statute.get('description') or statute.get('text') or 'N/A'
                                penalty = statute.get('penalties') or statute.get('penalty') or 'N/A'
                                
                                with st.expander(f"**{section_name}** - {title}"):
                                    st.markdown(f"**Provision/Scope:**  \n{desc}")
                                    st.markdown(f"**Enforcement / Penalties:**  \n{penalty}")
                        else:
                            st.info("No specific statutes confidently matched.")
                            
                    with q_tab3:
                        st.markdown("### 📚 Similar Precedents (FAISS Retrieval)")
                        precedents = res.get("precedents", [])
                        if precedents:
                            for idx, case in enumerate(precedents, 1):
                                name = case.get('case_name') or case.get('citation') or f"Case #{idx}"
                                year = case.get('year') or 'N/A'
                                court = case.get('court') or 'N/A'
                                facts = case.get('facts') or 'N/A'
                                holding = case.get('holding') or 'N/A'
                                principle = case.get('principle') or 'N/A'
                                similarity = case.get('similarity') or case.get('score') or 0.0
                                
                                with st.expander(f"⚖️ {idx}. {name} ({year}) - [Match: {similarity*100:.1f}%]"):
                                    st.markdown(f"**Court:** {court}")
                                    st.markdown(f"**Key Case Facts:**  \n{facts}")
                                    st.markdown(f"**Court Decision / Holding:**  \n{holding}")
                                    if principle and principle != "N/A":
                                        st.markdown(f"**Legal Principle Established:**  \n{principle}")
                        else:
                            st.info("No highly relevant case precedents found in database.")
        
        
        # --- TAB 2: FIR DOCUMENT ANALYSIS ---
        elif app_mode == "📄 FIR Document Analysis":
            st.markdown("### 📄 Upload First Information Report (FIR)")
            st.write("Upload a scanned image (JPG, JPEG, PNG) or digital PDF copy of the FIR document to extract details and analyze legal implications.")
            
            uploaded_file = st.file_uploader(
                "Choose an FIR file...",
                type=["pdf", "jpg", "jpeg", "png"],
                help="Supported: PDF, JPG, JPEG, PNG",
                key="fir_uploader"
            )
            
            col1, col2 = st.columns([5, 1])
            with col2:
                analyze_fir_btn = st.button("🔍 Analyze FIR Document", type="primary", use_container_width=True)
                
            if analyze_fir_btn and uploaded_file is not None:
                # Reset chat history for a new FIR analysis
                st.session_state.fir_chat_history = []
                with st.status("🔍 Legal AI System Processing...", expanded=True) as status:
                    status.write("📝 Analyzing FIR...")
                    status.write("📚 Retrieving Legal References...")
                    status.write("💡 Generating Legal Analysis...")
                    try:
                        start_time = time.time()
                        
                        # Format multipart file upload
                        files = {
                            "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                        }
                        
                        headers = {"Authorization": f"Bearer {st.session_state.auth_token}"}
                        response = requests.post(
                            f"{API_BASE_URL}/api/analyze-fir",
                            files=files,
                            headers=headers,
                            timeout=API_TIMEOUT
                        )
                        elapsed = time.time() - start_time
                        
                        if response.status_code == 401:
                            st.session_state.authenticated = False
                            st.session_state.auth_token = None
                            st.error("Session expired. Please log in again.")
                            time.sleep(1)
                            st.rerun()
                            
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.fir_results = {
                                "data": data,
                                "elapsed": elapsed
                            }
                            status.update(label="✅ FIR Analysis Report Generated!", state="complete", expanded=False)
                        else:
                            status.update(label="❌ API Error", state="error", expanded=True)
                            st.error(f"❌ API returned status code {response.status_code}")
                            try:
                                st.write(response.json())
                            except:
                                st.write(response.text)
                    except Exception as e:
                        status.update(label="❌ Connection/Processing Failed", state="error", expanded=True)
                        st.error("❌ Connection/Processing Failed. Unable to analyze the FIR document.")
                        st.info("Please verify that the FastAPI backend server is running on port 8000 and that Tesseract OCR/pypdf dependencies are correctly configured.")
        
            # Render FIR Results
            if st.session_state.fir_results:
                f_res = st.session_state.fir_results["data"]
                
                # Display warning if partial success due to LLM failure/timeout
                if f_res.get("status") == "partial_success":
                    st.warning("⚠️ **Connection Timeout / Fallback:** Qwen generated no final answer. Showing fallback legal analysis based on matching statutes and precedents.")
                
                # Risk Badge Class selection
                risk_lvl = f_res.get("risk_level", "Medium")
                if risk_lvl == "High":
                    risk_badge = f"<span class='risk-high'>⚠️ Risk: {risk_lvl}</span>"
                elif risk_lvl == "Low":
                    risk_badge = f"<span class='risk-low'>✅ Risk: {risk_lvl}</span>"
                elif risk_lvl == "Critical":
                    risk_badge = f"<span class='risk-high' style='background: rgba(139, 0, 0, 0.15); border-color: rgba(139, 0, 0, 0.35); color: #ff4d4d;'>🚨 Risk: {risk_lvl}</span>"
                else:
                    risk_badge = f"<span class='risk-medium'>⚠️ Risk: {risk_lvl}</span>"
                    
                topic_str = f_res.get("topic", "N/A").replace('_', ' ').title()
                
                # Helper function for manual review highlighting in table cells
                def get_field_html(res_dict: dict, field_key: str, label: str, is_last: bool = False):
                    val = res_dict.get(field_key)
                    review_fields = res_dict.get("review_required_fields", [])
                    
                    # Format list values
                    if isinstance(val, list):
                        if not val or val == ["Review Required"]:
                            val = "Review Required"
                        else:
                            if field_key in ["witnesses", "witnesses_list"]:
                                val = "<br>".join([f"{idx}. {w}" for idx, w in enumerate(val, 1)])
                            else:
                                val = "<br>".join(val)
                    elif not val:
                        val = "Review Required"
                        
                    # Replace newlines with <br> for HTML rendering
                    if isinstance(val, str) and "\n" in val:
                        val = val.replace("\n", "<br>")
                        
                    is_review = (field_key in review_fields) or (val == "Review Required") or (val == "Not found")
                    
                    if is_review:
                        display_val = f"<span style='background-color: rgba(255, 75, 75, 0.15); border: 1px solid rgba(255, 75, 75, 0.4); color: #ff4b4b; font-weight: 600; padding: 2px 8px; border-radius: 4px; font-size: 13px; display: inline-block;'>⚠️ Review Required</span>"
                    else:
                        display_val = f"<span style='color: #ffffff; font-weight: 500;'>{val}</span>"
                        
                    border_style = "" if is_last else "border-bottom: 1px solid #2d3748;"
                    return f"<tr style='{border_style}'><td style='padding: 8px 0; color: #a0aec0; width: 40%; font-weight: 500;'>{label}</td><td style='padding: 8px 0;'>{display_val}</td></tr>"
        
                # Metadata Header Row
                st.markdown(clean_html(f"""
                <div style='margin-bottom: 20px;'>
                    <span class='metric-badge'>📁 FIR Number: {f_res.get('fir_number', 'N/A')}</span>
                    <span class='metric-badge'>🏢 Police Station: {f_res.get('police_station', 'N/A')}</span>
                    <span class='metric-badge'>📌 Category: {topic_str}</span>
                    {risk_badge}
                </div>
                """), unsafe_allow_html=True)
                
                # Sub-tabs within FIR Document Analysis
                f_tab1, f_tab2, f_tab3 = st.tabs(["📊 Legal Intelligence Brief", "💬 Interactive Case Chat", "📄 Raw Transcribed Text"])
                
                with f_tab1:
                    st.markdown("### 📋 Case Analysis & Legal Intelligence Report")
                    
                    # Row 1: FIR Information & Involved Parties
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # FIR Profile table
                        fir_info_html = f"""
                        <div class='info-card' style='height: 100%; min-height: 380px;'>
                            <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>🏛️</span>1. FIR Information</h4>
                            <table style='width:100%; border-collapse: collapse; margin-top: 10px;'>
                                {get_field_html(f_res, 'fir_number', 'FIR Number')}
                                {get_field_html(f_res, 'police_station', 'Police Station')}
                                {get_field_html(f_res, 'date_of_registration', 'Registration Date')}
                                {get_field_html(f_res, 'date_of_incident', 'Incident Date')}
                                {get_field_html(f_res, 'location', 'Incident Location')}
                                {get_field_html(f_res, 'officer_details', 'Investigating Officer')}
                                {get_field_html(f_res, 'evidence_submitted', 'Evidence Submitted', is_last=True)}
                            </table>
                        </div>
                        """
                        st.markdown(clean_html(fir_info_html), unsafe_allow_html=True)
                        
                    with col2:
                        # Involved Parties table
                        involved_parties_html = f"""
                        <div class='info-card' style='height: 100%; min-height: 380px;'>
                            <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>👥</span>2. Involved Parties</h4>
                            <table style='width:100%; border-collapse: collapse; margin-top: 10px;'>
                                {get_field_html(f_res, 'complainant', 'Complainant')}
                                {get_field_html(f_res, 'accused', 'Accused Details')}
                                {get_field_html(f_res, 'witnesses', 'Involved Witnesses', is_last=True)}
                            </table>
                        </div>
                        """
                        st.markdown(clean_html(involved_parties_html), unsafe_allow_html=True)
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Row 2: Legal Risk Profile Dashboard
                    st.markdown("#### ⚖️ Legal Risk Profile")
                    risk_data = f_res.get("risk_assessment", {})
                    r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns(5)
                    
                    def make_risk_card(label: str, value: str):
                        val_upper = str(value).upper()
                        if val_upper == "CRITICAL":
                            bg = "rgba(139, 0, 0, 0.2)"
                            border = "rgba(139, 0, 0, 0.6)"
                            color = "#ff4d4d"
                        elif val_upper == "HIGH":
                            bg = "rgba(255, 75, 75, 0.15)"
                            border = "rgba(255, 75, 75, 0.4)"
                            color = "#ff4b4b"
                        elif val_upper == "LOW":
                            bg = "rgba(0, 204, 102, 0.15)"
                            border = "rgba(0, 204, 102, 0.4)"
                            color = "#00cc66"
                        else:  # MEDIUM
                            bg = "rgba(255, 165, 0, 0.15)"
                            border = "rgba(255, 165, 0, 0.4)"
                            color = "#ffa500"
                            
                        return f"""
                        <div class="risk-card" style="background-color: {bg}; border: 1px solid {border};">
                            <div class="risk-card-title">{label}</div>
                            <div class="risk-card-value" style="color: {color};">{value}</div>
                        </div>
                        """
                    
                    with r_col1:
                        st.markdown(make_risk_card("Overall Severity", risk_data.get("severity", risk_lvl)), unsafe_allow_html=True)
                    with r_col2:
                        st.markdown(make_risk_card("Financial Risk", risk_data.get("financial_risk", "Medium")), unsafe_allow_html=True)
                    with r_col3:
                        st.markdown(make_risk_card("Criminal Exposure", risk_data.get("criminal_exposure", "Medium")), unsafe_allow_html=True)
                    with r_col4:
                        st.markdown(make_risk_card("Complexity", risk_data.get("complexity", "Medium")), unsafe_allow_html=True)
                    with r_col5:
                        st.markdown(make_risk_card("Evidence Strength", risk_data.get("evidence_strength", "Medium")), unsafe_allow_html=True)
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Row 3: Case Timeline & Legal Sections (expandable cards)
                    import re
                    
                    def parse_incident_dates(incident_date_str: str):
                        if not incident_date_str or incident_date_str == "Review Required":
                            return []
                        # Find dates of formats like 18 July 2025 or 18 Jul 2025 or 18-07-2025
                        date_pattern = r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b|\b\d{1,2}[/\-\.]\d{1,2}[/\-\.](?:19|20)\d{2}\b'
                        matches = re.findall(date_pattern, incident_date_str, re.IGNORECASE)
                        return [m.strip() for m in matches]
        
                    def generate_timeline_events(res_dict):
                        events = []
                        raw_text = res_dict.get("extracted_text") or res_dict.get("incident_description") or res_dict.get("raw_text") or ""
                        inc_date = res_dict.get("date_of_incident")
                        reg_date = res_dict.get("date_of_registration")
                        
                        inc_dates = parse_incident_dates(inc_date)
                        reg_dates = parse_incident_dates(reg_date)
                        if not reg_dates and reg_date and reg_date != "Review Required":
                            reg_dates = [reg_date]
                            
                        def format_event_date(d_str):
                            cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', d_str).strip()
                            for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                                try:
                                    dt = datetime.strptime(cleaned, fmt)
                                    return dt.strftime("%d %b %Y")
                                except ValueError:
                                    continue
                            return d_str
        
                        text_lower = raw_text.lower()
                        
                        start_date = inc_dates[0] if len(inc_dates) > 0 else (inc_date if inc_date != "Review Required" else None)
                        end_date = inc_dates[-1] if len(inc_dates) > 1 else start_date
                        registration_date = reg_dates[0] if len(reg_dates) > 0 else (reg_date if reg_date != "Review Required" else None)
                        
                        if start_date:
                            if "call" in text_lower or "phone" in text_lower:
                                events.append({
                                    "date": format_event_date(start_date),
                                    "event": "Fraudulent phone call received"
                                })
                            if "otp" in text_lower or "password" in text_lower:
                                events.append({
                                    "date": format_event_date(start_date),
                                    "event": "OTP shared with caller"
                                })
                                
                        if end_date:
                            if "transaction" in text_lower or "transactions" in text_lower or "unauthorized" in text_lower:
                                events.append({
                                    "date": format_event_date(end_date),
                                    "event": "Unauthorized transactions detected"
                                })
                                
                        if registration_date:
                            events.append({
                                "date": format_event_date(registration_date),
                                "event": "FIR Registered"
                            })
                            if "complaint" in text_lower or "police station" in text_lower:
                                events.append({
                                    "date": format_event_date(registration_date),
                                    "event": "Complaint lodged with Cyber Crime Police Station"
                                })
                                
                        def get_sort_key(ev):
                            d_str = ev["date"]
                            cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', d_str).strip()
                            for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                                try:
                                    return datetime.strptime(cleaned, fmt)
                                except ValueError:
                                    continue
                            return datetime.max
                            
                        try:
                            events.sort(key=get_sort_key)
                        except Exception:
                            pass
                            
                        if not events:
                            if start_date:
                                events.append({
                                    "date": format_event_date(start_date),
                                    "event": "Occurrence of incident / offence"
                                })
                            if registration_date:
                                events.append({
                                    "date": format_event_date(registration_date),
                                    "event": "FIR registered with police station"
                                })
                        return events
        
                    LEGAL_SECTION_DATABASE = {
                        "IPC 420": {
                            "title": "Cheating and dishonestly inducing delivery of property",
                            "punishment": "Up to 7 years imprisonment and fine",
                            "type": "Cognizable",
                            "bail": "Non-bailable"
                        },
                        "IPC 468": {
                            "title": "Forgery for purpose of cheating",
                            "punishment": "Up to 7 years imprisonment and fine",
                            "type": "Cognizable",
                            "bail": "Non-bailable"
                        },
                        "IPC 471": {
                            "title": "Using forged document as genuine",
                            "punishment": "Same as forgery (Up to 7 years imprisonment and fine)",
                            "type": "Cognizable",
                            "bail": "Depends on the forged document's nature"
                        },
                        "IT Act 66C": {
                            "title": "Identity Theft",
                            "punishment": "Up to 3 years imprisonment and fine up to Rs. 1 lakh",
                            "type": "Cognizable",
                            "bail": "Bailable"
                        },
                        "IT Act 66D": {
                            "title": "Cheating by personation using computer resources",
                            "punishment": "Up to 3 years imprisonment and fine up to Rs. 1 lakh",
                            "type": "Cognizable",
                            "bail": "Bailable"
                        }
                    }
        
                    # 1. Timeline Events
                    timeline_events = f_res.get("timeline", [])
                    if not timeline_events or len(timeline_events) <= 2:
                        generated_events = generate_timeline_events(f_res)
                        if generated_events:
                            timeline_events = generated_events
        
                    # 2. Extracted Legal Sections
                    legal_sections = f_res.get("legal_sections", [])
                    crpc_list = f_res.get("crpc_sections", [])
        
                    # Debugging prints
                    print("Timeline Events:", timeline_events)
                    print("Extracted Legal Sections:", legal_sections)
        
                    # Warning Messages & Card rendering logic
                    if not timeline_events:
                        st.warning("⚠️ No timeline events could be extracted from this FIR.")
                    if not legal_sections:
                        st.warning("⚠️ No legal sections identified in FIR.")
        
                    if timeline_events and legal_sections:
                        t_col, s_col = st.columns(2)
                        with t_col:
                            timeline_html = """
                            <div class='info-card' style='min-height: 400px;'>
                                <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>📅</span>3. Case Timeline</h4>
                            """
                            for item in timeline_events:
                                t_date = item.get("date", "N/A")
                                t_event = item.get("event", "N/A")
                                timeline_html += f"""
                                <div class="timeline-item">
                                    <div class="timeline-dot"></div>
                                    <div class="timeline-date">{t_date}</div>
                                    <div class="timeline-event">{t_event}</div>
                                </div>
                                """
                            timeline_html += "</div>"
                            st.markdown(clean_html(timeline_html), unsafe_allow_html=True)
                            
                        with s_col:
                            explainers_html = """
                            <div class='info-card' style='min-height: 400px;'>
                                <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>📖</span>4. Legal Sections Explainers</h4>
                            """
                            for sec in legal_sections:
                                sec_norm = sec.strip()
                                found_key = None
                                for k in LEGAL_SECTION_DATABASE.keys():
                                    if k.lower() == sec_norm.lower().replace("it act", "it act").replace("it", "it act"):
                                        found_key = k
                                        break
                                if not found_key:
                                    for k in LEGAL_SECTION_DATABASE.keys():
                                        if k.lower().replace(" ", "") in sec_norm.lower().replace(" ", "") or sec_norm.lower().replace(" ", "") in k.lower().replace(" ", ""):
                                            found_key = k
                                            break
                                            
                                # Check backend explainers fallback if not in frontend database
                                backend_exp = None
                                if not found_key:
                                    backend_explainers = f_res.get("statutes_explainers", {})
                                    sec_norm_clean = sec_norm.lower().replace(" ", "").replace("-", "")
                                    for b_k, b_v in backend_explainers.items():
                                        b_k_clean = b_k.lower().replace(" ", "").replace("-", "")
                                        if b_k_clean == sec_norm_clean or b_k_clean in sec_norm_clean or sec_norm_clean in b_k_clean:
                                            backend_exp = b_v
                                            break
        
                                if found_key:
                                    exp = LEGAL_SECTION_DATABASE[found_key]
                                    title = exp.get('title')
                                    punishment = exp.get('punishment')
                                    type_val = exp.get('type')
                                    bail = exp.get('bail')
                                elif backend_exp:
                                    title = backend_exp.get('name')
                                    punishment = backend_exp.get('punishment') or backend_exp.get('description')
                                    type_val = backend_exp.get('cognizability')
                                    bail = backend_exp.get('bailability')
                                else:
                                    title = None
        
                                if title:
                                    explainers_html += f"""
                                    <details style="margin-bottom: 10px; border: 1px solid #2d3748; border-radius: 6px; background-color: #1a202c; padding: 10px;">
                                        <summary style="font-weight: 600; cursor: pointer; color: #e2e8f0; outline: none;">📖 {sec_norm} - {title}</summary>
                                        <div style="margin-top: 10px; padding-left: 10px; border-left: 2px solid #d4af37; color: #a0aec0; font-size: 14px;">
                                            <div style="margin-bottom: 4px;"><strong style="color: #ffffff;">Title:</strong> {title}</div>
                                            <div style="margin-bottom: 4px;"><strong style="color: #ffffff;">Punishment:</strong> {punishment}</div>
                                            <div style="margin-bottom: 4px;"><strong style="color: #ffffff;">Type:</strong> {type_val}</div>
                                            <div style="margin-bottom: 4px;"><strong style="color: #ffffff;">Bail:</strong> {bail}</div>
                                        </div>
                                    </details>
                                    """
                                else:
                                    explainers_html += f"""
                                    <details style="margin-bottom: 10px; border: 1px solid #2d3748; border-radius: 6px; background-color: #1a202c; padding: 10px;">
                                        <summary style="font-weight: 600; cursor: pointer; color: #e2e8f0; outline: none;">📖 {sec_norm}</summary>
                                        <div style="margin-top: 10px; padding-left: 10px; border-left: 2px solid #ff4b4b; color: #ff4b4b; font-size: 14px;">
                                            Explanation currently unavailable.
                                        </div>
                                    </details>
                                    """
                                    
                            crpc_list = f_res.get("crpc_sections", [])
                            if crpc_list:
                                explainers_html += "<div style='margin-top: 15px; font-weight: 600; color: #a0aec0; font-size: 13px; text-transform: uppercase;'>CrPC / BNSS Procedural Sections:</div>"
                                for c_sec in crpc_list:
                                    explainers_html += f"<div style='margin-top: 4px; color: #ffffff; font-size: 14px;'>- <strong>{c_sec}</strong></div>"
                            explainers_html += "</div>"
                            st.markdown(clean_html(explainers_html), unsafe_allow_html=True)
        
                    elif timeline_events:
                        timeline_html = """
                        <div class='info-card' style='min-height: 400px;'>
                            <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>📅</span>3. Case Timeline</h4>
                        """
                        for item in timeline_events:
                            t_date = item.get("date", "N/A")
                            t_event = item.get("event", "N/A")
                            timeline_html += f"""
                            <div class="timeline-item">
                                <div class="timeline-dot"></div>
                                <div class="timeline-date">{t_date}</div>
                                <div class="timeline-event">{t_event}</div>
                            </div>
                            """
                        timeline_html += "</div>"
                        st.markdown(clean_html(timeline_html), unsafe_allow_html=True)
        
                    elif legal_sections:
                        explainers_html = """
                        <div class='info-card' style='min-height: 400px;'>
                            <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>📖</span>4. Legal Sections Explainers</h4>
                        """
                        for sec in legal_sections:
                            sec_norm = sec.strip()
                            found_key = None
                            for k in LEGAL_SECTION_DATABASE.keys():
                                if k.lower() == sec_norm.lower().replace("it act", "it act").replace("it", "it act"):
                                    found_key = k
                                    break
                            if not found_key:
                                for k in LEGAL_SECTION_DATABASE.keys():
                                    if k.lower().replace(" ", "") in sec_norm.lower().replace(" ", "") or sec_norm.lower().replace(" ", "") in k.lower().replace(" ", ""):
                                        found_key = k
                                        break
                                        
                            # Check backend explainers fallback if not in frontend database
                            backend_exp = None
                            if not found_key:
                                backend_explainers = f_res.get("statutes_explainers", {})
                                sec_norm_clean = sec_norm.lower().replace(" ", "").replace("-", "")
                                for b_k, b_v in backend_explainers.items():
                                    b_k_clean = b_k.lower().replace(" ", "").replace("-", "")
                                    if b_k_clean == sec_norm_clean or b_k_clean in sec_norm_clean or sec_norm_clean in b_k_clean:
                                            backend_exp = b_v
                                            break
        
                            if found_key:
                                exp = LEGAL_SECTION_DATABASE[found_key]
                                title = exp.get('title')
                                punishment = exp.get('punishment')
                                type_val = exp.get('type')
                                bail = exp.get('bail')
                            elif backend_exp:
                                title = backend_exp.get('name')
                                punishment = backend_exp.get('punishment') or backend_exp.get('description')
                                type_val = backend_exp.get('cognizability')
                                bail = backend_exp.get('bailability')
                            else:
                                title = None
        
                            if title:
                                explainers_html += f"""
                                <details style="margin-bottom: 10px; border: 1px solid #2d3748; border-radius: 6px; background-color: #1a202c; padding: 10px;">
                                    <summary style="font-weight: 600; cursor: pointer; color: #e2e8f0; outline: none;">📖 {sec_norm} - {title}</summary>
                                    <div style="margin-top: 10px; padding-left: 10px; border-left: 2px solid #d4af37; color: #a0aec0; font-size: 14px;">
                                        <div style="margin-bottom: 4px;"><strong style="color: #ffffff;">Title:</strong> {title}</div>
                                        <div style="margin-bottom: 4px;"><strong style="color: #ffffff;">Punishment:</strong> {punishment}</div>
                                        <div style="margin-bottom: 4px;"><strong style="color: #ffffff;">Type:</strong> {type_val}</div>
                                        <div style="margin-bottom: 4px;"><strong style="color: #ffffff;">Bail:</strong> {bail}</div>
                                    </div>
                                </details>
                                """
                            else:
                                explainers_html += f"""
                                <details style="margin-bottom: 10px; border: 1px solid #2d3748; border-radius: 6px; background-color: #1a202c; padding: 10px;">
                                    <summary style="font-weight: 600; cursor: pointer; color: #e2e8f0; outline: none;">📖 {sec_norm}</summary>
                                    <div style="margin-top: 10px; padding-left: 10px; border-left: 2px solid #ff4b4b; color: #ff4b4b; font-size: 14px;">
                                        Explanation currently unavailable.
                                    </div>
                                </details>
                                """
                                
                        crpc_list = f_res.get("crpc_sections", [])
                        if crpc_list:
                            explainers_html += "<div style='margin-top: 15px; font-weight: 600; color: #a0aec0; font-size: 13px; text-transform: uppercase;'>CrPC / BNSS Procedural Sections:</div>"
                            for c_sec in crpc_list:
                                explainers_html += f"<div style='margin-top: 4px; color: #ffffff; font-size: 14px;'>- <strong>{c_sec}</strong></div>"
                        explainers_html += "</div>"
                        st.markdown(clean_html(explainers_html), unsafe_allow_html=True)
        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Row 4: AI Legal Analysis
                    advice = f_res.get("legal_advice", "")
                    
                    try:
                        sections = parse_legal_advice_to_sections(advice)
                        if not sections:
                            sections = {}
                    except Exception:
                        sections = {}
                    
                    st.markdown(clean_html("""
                    <div class='info-card'>
                        <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>💡</span>5. AI Legal Analysis & Findings</h4>
                    """), unsafe_allow_html=True)
                    
                    if sections:
                        st.markdown(sections.get("analysis", advice))
                    else:
                        st.markdown(advice)
                    st.markdown("</div>", unsafe_allow_html=True)
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Row 5: Related Precedents
                    st.markdown(clean_html("""
                    <div class='info-card'>
                        <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>📚</span>7. Related Precedents (FAISS Database Matches)</h4>
                    """), unsafe_allow_html=True)
                    
                    precedents = f_res.get("precedents", [])
                    if precedents:
                        for idx, prec in enumerate(precedents, 1):
                            p_name = prec.get("case_name", "Unknown Case")
                            p_court = prec.get("court", "Court Unknown")
                            p_year = prec.get("year", "Year Unknown")
                            p_facts = prec.get("facts", "Facts not available")
                            p_holding = prec.get("holding", "Holding not available")
                            p_score = prec.get("similarity_score") or prec.get("score") or 0.0
                            
                            st.markdown(clean_html(f"""
                            <div style='background-color: #1a202c; border: 1px solid #2d3748; border-radius: 8px; padding: 15px; margin-bottom: 12px;'>
                                <div style='display: flex; justify-content: space-between; align-items: center;'>
                                    <strong style='font-size: 15px; color: #d4af37;'>⚖️ {idx}. {p_name} ({p_year})</strong>
                                    <span class='metric-badge' style='margin: 0;'>Match: {p_score*100:.1f}%</span>
                                </div>
                                <div style='font-size: 13px; color: #a0aec0; margin-top: 4px; font-weight: 500;'>Court: {p_court}</div>
                                <div style='font-size: 14px; color: #e2e8f0; margin-top: 8px;'><strong>Facts:</strong> {p_facts}</div>
                                <div style='font-size: 14px; color: #e2e8f0; margin-top: 6px;'><strong>Court Observation / Holding:</strong> {p_holding}</div>
                            </div>
                            """), unsafe_allow_html=True)
                    else:
                        st.info("No relevant precedent judgments found in local vector database.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Row 6: Export & Disclaimer
                    st.markdown(clean_html("""
                    <div class='info-card'>
                        <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>📥</span>8. Export Brief & Report</h4>
                        <p style='color: #a0aec0; font-size: 14px;'>Download the complete structured legal analysis report as an offline document or print it directly.</p>
                    </div>
                    """), unsafe_allow_html=True)
                    
                    # Report Content formatting for MD export
                    report_content = f"""# LEGAL RESEARCH & ANALYSIS REPORT
        Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Powered by Indian Legal Advisor RAG Engine
        
        ================================================================================
        1. FIR INFORMATION
        ================================================================================
        - FIR Number: {f_res.get('fir_number', 'N/A')}
        - Police Station: {f_res.get('police_station', 'N/A')}
        - Date of Incident: {f_res.get('date_of_incident', 'N/A')}
        - Category (Topic): {topic_str}
        - Location: {f_res.get('location', 'N/A')}
        - Investigating Officer: {f_res.get('officer_details', 'N/A')}
        - Evidence Submitted: {f_res.get('evidence_submitted', 'N/A')}
        
        ================================================================================
        2. INVOLVED PARTIES
        ================================================================================
        - Complainant: {f_res.get('complainant', 'N/A')}
        - Accused: {f_res.get('accused', 'N/A')}
        - Witnesses: {f_res.get('witnesses_str', 'N/A')}
        
        ================================================================================
        3. LEGAL RISK PROFILE
        ================================================================================
        - Overall Severity: {risk_data.get('severity', risk_lvl)}
        - Financial Risk: {risk_data.get('financial_risk', 'Medium')}
        - Criminal Exposure: {risk_data.get('criminal_exposure', 'Medium')}
        - Complexity: {risk_data.get('complexity', 'Medium')}
        - Evidence Strength: {risk_data.get('evidence_strength', 'Medium')}
        
        ================================================================================
        4. LEGAL SECTIONS
        ================================================================================
        - IPC / BNS Sections: {", ".join(legal_sections) if legal_sections else "None"}
        - CrPC / BNSS Sections: {", ".join(crpc_list) if crpc_list else "None"}
        
        ================================================================================
        5. AI LEGAL ANALYSIS
        ================================================================================
        {sections.get('analysis') or advice}
        
        ================================================================================
        6. RECOMMENDATIONS
        ================================================================================
        {sections.get('recommendations') or "No recommendations detailed."}
        
        ================================================================================
        7. SIMILAR PRECEDENTS
        ================================================================================
        """
                    for idx, prec in enumerate(precedents, 1):
                        report_content += f"\n{idx}. {prec.get('case_name')} ({prec.get('year')})\n   Court: {prec.get('court')}\n   Holding: {prec.get('holding')}\n"
                        
                    report_content += """
        ================================================================================
        LEGAL DISCLAIMER
        ================================================================================
        This platform provides legal research assistance and informational analysis only. It does not constitute legal advice or create an attorney-client relationship. Users should consult a qualified advocate for professional legal guidance.
        """
                    
                    exp_col1, exp_col2, exp_col3 = st.columns(3)
                    with exp_col1:
                        st.download_button(
                            label="📥 Download Markdown Brief",
                            data=report_content,
                            file_name=f"Legal_Report_FIR_{f_res.get('fir_number', 'Unknown').replace('/', '_')}.md",
                            mime="text/markdown",
                            use_container_width=True
                        )
                    with exp_col2:
                        # PDF Generation via PDFGenerator
                        from src.utils.pdf_generator import PDFGenerator
                        try:
                            pdf_bytes = PDFGenerator.generate_report(f_res)
                            st.download_button(
                                label="📥 Download PDF Case Brief",
                                data=pdf_bytes,
                                file_name=f"Legal_Brief_FIR_{f_res.get('fir_number', 'Unknown').replace('/', '_')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        except Exception as pdf_e:
                            st.error(f"Error compiling PDF: {pdf_e}")
                    with exp_col3:
                        if st.button("🖨️ Print Analysis Report", use_container_width=True):
                            st.info("💡 **Print Tip**: Use your browser print shortcut (**Ctrl+P** or **Cmd+P** on Mac) to print this page. The layout is optimized to print clean reports.")
                    
                    # Bottom Disclaimer Block
                    st.markdown(clean_html("""
                    <div style='background-color: rgba(214, 158, 46, 0.05); border: 1px solid rgba(214, 158, 46, 0.25); border-radius: 8px; padding: 15px; margin-top: 25px;'>
                        <div style='font-weight: 700; color: #d69e2e; font-size: 13px; text-transform: uppercase;'>⚖️ Legal Disclaimer</div>
                        <div style='color: #a0aec0; font-size: 12px; margin-top: 4px; line-height: 1.5;'>
                            This platform provides legal research assistance and informational analysis only. It does not constitute legal advice or create an attorney-client relationship. Users should consult a qualified advocate for professional legal guidance.
                        </div>
                    </div>
                    """), unsafe_allow_html=True)
                    
                with f_tab2:
                    st.markdown("### 💬 Interactive Chat with FIR Context")
                    st.markdown("Ask specific questions about the offences, evidence, punishments, or recommended next steps based on the uploaded FIR document.")
                    
                    if "fir_chat_history" not in st.session_state:
                        st.session_state.fir_chat_history = []
                        
                    # Display chat history
                    for msg in st.session_state.fir_chat_history:
                        with st.chat_message(msg["role"]):
                            st.write(msg["content"])
                            
                    # Chat input
                    user_question = st.chat_input("Ask a question about this FIR...")
                    if user_question:
                        # Display user question
                        with st.chat_message("user"):
                            st.write(user_question)
                        
                        # Append to history
                        st.session_state.fir_chat_history.append({"role": "user", "content": user_question})
                        
                        # Call chat API
                        with st.spinner("🤖 AI is reviewing FIR context and drafting response..."):
                            try:
                                headers = {"Authorization": f"Bearer {st.session_state.auth_token}"}
                                chat_resp = requests.post(
                                    f"{API_BASE_URL}/api/chat-fir",
                                    json={
                                        "text": f_res.get("extracted_text", ""),
                                        "question": user_question,
                                        "history": st.session_state.fir_chat_history
                                    },
                                    headers=headers,
                                    timeout=API_TIMEOUT
                                )
                                if chat_resp.status_code == 401:
                                    st.session_state.authenticated = False
                                    st.session_state.auth_token = None
                                    st.error("Session expired. Please log in again.")
                                    time.sleep(1)
                                    st.rerun()
                                    
                                if chat_resp.status_code == 200:
                                    ai_answer = chat_resp.json().get("response", "I could not generate an answer.")
                                    # Append to history
                                    st.session_state.fir_chat_history.append({"role": "assistant", "content": ai_answer})
                                    st.rerun()
                                else:
                                    st.error(f"Error communicating with Chat API: {chat_resp.status_code}")
                            except Exception as chat_e:
                                st.error(f"Failed to reach Chat API: {chat_e}")
                                
                with f_tab3:
                    # Show raw OCR text inside a text area
                    st.text_area(
                        "Extracted Text content:",
                        value=f_res.get("extracted_text", "No text extracted."),
                        height=500,
                        disabled=True
                    )
        
        elif app_mode == "🔎 Legal Notice Analysis":
            st.markdown("### 🔎 Legal Notice Analysis")
            st.write("Upload a legal notice document (PDF, JPG, JPEG, PNG) to extract its text and generate an AI-assisted analysis and plain-language explanation.")
        
            # Show supported notice types in an expander for reference
            with st.expander("📋 Supported Legal Notice Types"):
                col_type1, col_type2 = st.columns(2)
                with col_type1:
                    st.markdown("""
                    - 📑 **Copyright Infringement Notice**
                    - 🏷️ **Trademark Notice**
                    - 🗣️ **Defamation Notice**
                    - 💰 **Money Recovery Notice**
                    - 🤝 **Contract Breach Notice**
                    """)
                with col_type2:
                    st.markdown("""
                    - 🏠 **Property Dispute Notice**
                    - 🛒 **Consumer Complaint Notice**
                    - 💼 **Employment Notice**
                    - 👨‍👩‍👧 **Family Law Notice**
                    - ⚖️ **Other advocate-issued notices**
                    """)
        
            uploaded_file = st.file_uploader(
                "Choose a Legal Notice file...",
                type=["pdf", "jpg", "jpeg", "png"],
                help="Supported formats: PDF, JPG, JPEG, PNG",
                key="notice_uploader"
            )
        
            col1, col2 = st.columns([5, 1])
            with col2:
                analyze_notice_btn = st.button("🔍 Analyze Notice", type="primary", use_container_width=True)
        
            if analyze_notice_btn and uploaded_file is not None:
                with st.status("🔍 Legal AI System Processing...", expanded=True) as status:
                    status.write("📝 Uploading & extracting text...")
                    status.write("🧠 Performing AI legal document analysis...")
                    try:
                        start_time = time.time()
                        files = {
                            "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                        }
                        headers = {"Authorization": f"Bearer {st.session_state.auth_token}"}
                        response = requests.post(
                            f"{API_BASE_URL}/api/analyze-notice",
                            files=files,
                            headers=headers,
                            timeout=API_TIMEOUT
                        )
                        elapsed = time.time() - start_time
                        
                        if response.status_code == 401:
                            st.session_state.authenticated = False
                            st.session_state.auth_token = None
                            st.error("Session expired. Please log in again.")
                            time.sleep(1)
                            st.rerun()
                            
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.notice_results = {
                                "data": data,
                                "elapsed": elapsed
                            }
                            status.update(label="✅ Legal Notice Analysis Complete!", state="complete", expanded=False)
                        else:
                            status.update(label="❌ API Error", state="error", expanded=True)
                            st.error(f"❌ API returned status code {response.status_code}")
                            try:
                                st.write(response.json())
                            except:
                                st.write(response.text)
                    except Exception as e:
                        status.update(label="❌ Connection/Processing Failed", state="error", expanded=True)
                        st.error("❌ Connection/Processing Failed. Unable to analyze the legal notice document.")
                        st.info("Please verify that the FastAPI backend server is running on port 8000.")
        
            # Render Notice Results
            if st.session_state.notice_results:
                n_res = st.session_state.notice_results["data"]
                
                sender = n_res.get("sender", "Not identified")
                recipient = n_res.get("recipient", "Not identified")
                advocate = n_res.get("advocate", "None")
                notice_date = n_res.get("notice_date", "Not specified")
                response_deadline = n_res.get("response_deadline", "Not specified")
        
                # Visual layout: Notice metadata side-by-side with general highlights
                col_meta, col_summary_card = st.columns([2, 3])
        
                with col_meta:
                    # Metadata Table
                    metadata_html = f"""
                    <div class='info-card' style='height: 100%; min-height: 280px;'>
                        <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>🏛️</span>Notice Info</h4>
                        <table style='width:100%; border-collapse: collapse; margin-top: 10px;'>
                            <tr style='border-bottom: 1px solid #2d3748;'><td style='padding: 8px 0; color: #a0aec0; width: 40%; font-weight: 500;'>Sender</td><td style='padding: 8px 0; color: #ffffff; font-weight: 500;'>{sender}</td></tr>
                            <tr style='border-bottom: 1px solid #2d3748;'><td style='padding: 8px 0; color: #a0aec0; width: 40%; font-weight: 500;'>Recipient</td><td style='padding: 8px 0; color: #ffffff; font-weight: 500;'>{recipient}</td></tr>
                            <tr style='border-bottom: 1px solid #2d3748;'><td style='padding: 8px 0; color: #a0aec0; width: 40%; font-weight: 500;'>Advocate/Firm</td><td style='padding: 8px 0; color: #ffffff; font-weight: 500;'>{advocate}</td></tr>
                            <tr style='border-bottom: 1px solid #2d3748;'><td style='padding: 8px 0; color: #a0aec0; width: 40%; font-weight: 500;'>Date</td><td style='padding: 8px 0; color: #ffffff; font-weight: 500;'>{notice_date}</td></tr>
                            <tr style=''><td style='padding: 8px 0; color: #a0aec0; width: 40%; font-weight: 500;'>Deadline</td><td style='padding: 8px 0; color: #ff4b4b; font-weight: 600;'>⚠️ {response_deadline}</td></tr>
                        </table>
                    </div>
                    """
                    st.markdown(clean_html(metadata_html), unsafe_allow_html=True)
        
                with col_summary_card:
                    # Plain English Quick Brief
                    quick_brief_html = f"""
                    <div class='info-card' style='height: 100%; min-height: 280px; display: flex; flex-direction: column; justify-content: space-between;'>
                        <div>
                            <h4 style='margin-top:0; color:#d4af37;'><span style='margin-right:8px;'>💡</span>Quick AI Overview</h4>
                            <p style='color: #e2e8f0; font-size: 14px; line-height: 1.6; margin-top: 10px;'>
                                {n_res.get("ai_explanation", "No summary available.")}
                            </p>
                        </div>
                        <div style='margin-top: 15px; border-top: 1px solid #2d3748; padding-top: 10px; font-size: 12px; color: #a0aec0;'>
                            ⏱️ Processed in {st.session_state.notice_results.get("elapsed", 0.0):.2f} seconds
                        </div>
                    </div>
                    """
                    st.markdown(clean_html(quick_brief_html), unsafe_allow_html=True)
        
                # Tabbed Details
                st.markdown("<br>", unsafe_allow_html=True)
                t_summary, t_sections, t_actions, t_steps = st.tabs([
                    "📑 Notice Summary",
                    "⚖️ Legal Sections",
                    "💡 AI Explanation",
                    "📌 Recommended Next Steps"
                ])
        
                with t_summary:
                    st.markdown("### 📑 Notice Summary")
                    st.markdown(n_res.get("notice_summary", "No summary available."))
                    
                    st.markdown("#### 🚨 Key Allegations")
                    allegations = n_res.get("key_allegations", [])
                    if allegations:
                        for item in allegations:
                            st.markdown(f"- 🔴 {item}")
                    else:
                        st.info("No explicit allegations identified.")
        
                with t_sections:
                    st.markdown("### ⚖️ Legal Provisions Cited")
                    provisions = n_res.get("legal_provisions", [])
                    if provisions:
                        for idx, prov in enumerate(provisions, 1):
                            sec_name = prov.get("section", "Statutory Section")
                            sec_exp = prov.get("explanation", "Explanation not available.")
                            with st.expander(f"📖 {idx}. {sec_name}"):
                                st.markdown(f"**Section/Provision:** {sec_name}")
                                st.markdown(f"**Plain Language Explanation:**  \n{sec_exp}")
                    else:
                        st.info("No specific statutory sections or laws cited in the notice.")
        
                with t_actions:
                    st.markdown("### 💡 Detailed AI Analysis")
                    
                    st.markdown("#### 📝 Demanded Actions")
                    st.write("What the sender asks you to do:")
                    actions = n_res.get("required_actions", [])
                    if actions:
                        for act in actions:
                            st.markdown(f"- 🔸 {act}")
                    else:
                        st.info("No specific demanded actions identified.")
        
                    st.markdown("#### ⚡ Possible Consequences if Ignored")
                    st.markdown(clean_html(f"""
                    <div style='background-color: rgba(255, 165, 0, 0.08); border-left: 4px solid #ffa500; border-radius: 4px; padding: 15px; margin-bottom: 20px;'>
                        <strong style='color: #ffa500;'>⚠️ Cautionary Note:</strong>
                        <p style='color: #e2e8f0; font-size: 14px; line-height: 1.5; margin-top: 5px; margin-bottom: 0;'>
                            {n_res.get("possible_consequences", "Failing to respond may result in legal actions.")}
                        </p>
                    </div>
                    """), unsafe_allow_html=True)
        
                with t_steps:
                    st.markdown("### 📌 Recommended Next Steps")
                    st.write("Based on the notice contents, we recommend taking the following actions:")
                    recs = n_res.get("recommendations", [])
                    if recs:
                        for rec in recs:
                            st.markdown(f"- 📍 {rec}")
                    else:
                        st.markdown("- 📍 Read the notice carefully.")
                        st.markdown("- 📍 Preserve all relevant documents and electronic communications.")
                        st.markdown("- 📍 Consider consulting a qualified advocate before responding.")
                        st.markdown("- 📍 Do not ignore response deadlines if specified.")
        
                # PDF and Raw text view expanders
                st.markdown("---")
                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    with st.expander("📄 View Raw Transcribed Text"):
                        st.text_area(
                            "Extracted Text content:",
                            value=n_res.get("extracted_text", "No text extracted."),
                            height=300,
                            disabled=True,
                            key="notice_raw_text"
                        )
                with col_exp2:
                    # Let's generate notice brief markdown export
                    notice_report = f"""# LEGAL NOTICE ANALYSIS REPORT
        Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Powered by Indian Legal Advisor Notice Analyzer
        
        ================================================================================
        1. NOTICE PROFILE
        ================================================================================
        - Sender: {sender}
        - Recipient: {recipient}
        - Advocate/Law Firm: {advocate}
        - Notice Date: {notice_date}
        - Response Deadline: {response_deadline}
        
        ================================================================================
        2. SUMMARY & ALLEGATIONS
        ================================================================================
        {n_res.get("notice_summary", "N/A")}
        
        Key Allegations:
        """
                    for item in allegations:
                        notice_report += f"- {item}\n"
                    notice_report += f"""
        ================================================================================
        3. CITED LAWS & SECTIONS
        ================================================================================
        """
                    for prov in provisions:
                        notice_report += f"- {prov.get('section')}: {prov.get('explanation')}\n"
                    notice_report += f"""
        ================================================================================
        4. AI EXPLANATION & DEMANDS
        ================================================================================
        {n_res.get("ai_explanation", "N/A")}
        
        Demanded Actions:
        """
                    for act in actions:
                        notice_report += f"- {act}\n"
                    notice_report += f"""
        Possible Consequences:
        {n_res.get("possible_consequences", "N/A")}
        
        ================================================================================
        5. RECOMMENDATIONS & NEXT STEPS
        ================================================================================
        """
                    for rec in recs:
                        notice_report += f"- {rec}\n"
                    notice_report += """
        ================================================================================
        DISCLAIMER
        ================================================================================
        This analysis is AI-generated for informational purposes only and is not legal advice. Consult a qualified advocate for advice specific to your situation.
        """
                    st.download_button(
                        label="📥 Download Notice Analysis Brief",
                        data=notice_report,
                        file_name=f"Legal_Notice_Analysis_{sender.replace(' ', '_')[:30]}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
        
                # Bottom Disclaimer Block
                st.markdown(clean_html("""
                <div style='background-color: rgba(255, 75, 75, 0.05); border-left: 4px solid #ff4b4b; border-radius: 4px; padding: 15px; margin-top: 25px;'>
                    <div style='font-weight: 700; color: #ff4b4b; font-size: 13px; text-transform: uppercase;'>⚠️ Disclaimer</div>
                    <div style='color: #a0aec0; font-size: 12px; margin-top: 4px; line-height: 1.5;'>
                        This analysis is AI-generated for informational purposes only and is not legal advice. Consult a qualified advocate for advice specific to your situation.
                    </div>
                </div>
                """), unsafe_allow_html=True)
        
        elif app_mode == "⚖️ Legal Notice":
            st.markdown("### ⚖️ Legal Notice")
            
            # 3. Highlighted Disclaimer banner
            st.markdown(clean_html("""
            <div style="
                background: rgba(255, 75, 75, 0.05); 
                border-left: 4px solid #ff4b4b; 
                padding: 15px 20px; 
                border-radius: 4px; 
                margin-bottom: 25px;
            ">
                <strong style="color: #ff4b4b;">⚠️ Disclaimer Notice:</strong>
                <span style="color: #e2e8f0; font-size: 14px; line-height: 1.5; margin-left: 5px;">
                    This application provides AI-assisted legal information and research support only. It is not a substitute for professional legal advice.
                </span>
            </div>
            """), unsafe_allow_html=True)
            
            # 1. "What is this?" section
            st.markdown("#### ℹ️ What is this?")
            st.markdown("""
            This section outlines the terms of service, liability limitations, and operational frameworks governing the 
            **Indian Legal Advisor** platform. It provides clear parameters on the scope of AI-assisted legal research, 
            data handling practices, and the educational nature of the tools provided. Users are requested to review 
            the quick summary cards below and acknowledge the official legal document.
            """)
            
            # 2. "Quick Summary" section with cards
            st.markdown("#### 📋 Quick Summary")
            
            col_summary1, col_summary2, col_summary3 = st.columns(3)
            
            with col_summary1:
                st.markdown(clean_html("""
                <div class="info-card" style="height: 160px; display: flex; flex-direction: column; justify-content: flex-start;">
                    <h5 style="color: #d4af37; margin-top: 0; margin-bottom: 8px;">🎯 Purpose</h5>
                    <p style="font-size: 13px; line-height: 1.5; color: #a0aec0; margin: 0;">
                        Provides preliminary legal research guidance, statutory mapping, and educational summaries for Indian legal topics.
                    </p>
                </div>
                """), unsafe_allow_html=True)
                st.markdown(clean_html("""
                <div class="info-card" style="height: 160px; display: flex; flex-direction: column; justify-content: flex-start;">
                    <h5 style="color: #d4af37; margin-top: 0; margin-bottom: 8px;">🔒 Privacy</h5>
                    <p style="font-size: 13px; line-height: 1.5; color: #a0aec0; margin: 0;">
                        All inputs and documents are processed securely. Avoid uploading highly confidential or personally sensitive information.
                    </p>
                </div>
                """), unsafe_allow_html=True)
                
            with col_summary2:
                st.markdown(clean_html("""
                <div class="info-card" style="height: 160px; display: flex; flex-direction: column; justify-content: flex-start;">
                    <h5 style="color: #d4af37; margin-top: 0; margin-bottom: 8px;">⚠️ No Legal Advice</h5>
                    <p style="font-size: 13px; line-height: 1.5; color: #a0aec0; margin: 0;">
                        AI-generated advisory reports are for educational reference only and do not constitute formal legal counsel.
                    </p>
                </div>
                """), unsafe_allow_html=True)
                st.markdown(clean_html("""
                <div class="info-card" style="height: 160px; display: flex; flex-direction: column; justify-content: flex-start;">
                    <h5 style="color: #d4af37; margin-top: 0; margin-bottom: 8px;">🤖 AI Generated Content</h5>
                    <p style="font-size: 13px; line-height: 1.5; color: #a0aec0; margin: 0;">
                        Content is compiled using InLegalBERT retrieval and LLM reasoning. Always cross-verify findings against official codes.
                    </p>
                </div>
                """), unsafe_allow_html=True)
                
            with col_summary3:
                st.markdown(clean_html("""
                <div class="info-card" style="height: 160px; display: flex; flex-direction: column; justify-content: flex-start;">
                    <h5 style="color: #d4af37; margin-top: 0; margin-bottom: 8px;">🤝 No Attorney-Client Relationship</h5>
                    <p style="font-size: 13px; line-height: 1.5; color: #a0aec0; margin: 0;">
                        Interaction with this assistant does not establish any professional contract or attorney-client relationship.
                    </p>
                </div>
                """), unsafe_allow_html=True)
                st.markdown(clean_html("""
                <div class="info-card" style="height: 160px; display: flex; flex-direction: column; justify-content: flex-start;">
                    <h5 style="color: #d4af37; margin-top: 0; margin-bottom: 8px;">👤 User Responsibility</h5>
                    <p style="font-size: 13px; line-height: 1.5; color: #a0aec0; margin: 0;">
                        Users must independently assess outcomes and consult a qualified, registered advocate before taking legal action.
                    </p>
                </div>
                """), unsafe_allow_html=True)
        
            # 4. Checkbox for understanding legal notice
            st.markdown("<br>", unsafe_allow_html=True)
            agreed = st.checkbox("I have read and understood the Legal Notice.", key="legal_notice_agreement")
            
            # 5. PDF Section (after summary)
            st.markdown("---")
            st.markdown("#### 📜 Official Legal Notice Document")
            
            pdf_path = root_dir / "assets" / "legal_notice.pdf"
            
            if pdf_path.exists():
                try:
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                        
                    # 6. Download PDF button
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.download_button(
                            label="📥 Download Legal Notice PDF",
                            data=pdf_bytes,
                            file_name="legal_notice.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    # 5. Display PDF below summary
                    import base64
                    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf" style="border: 1px solid #2d3748; border-radius: 12px; margin-top: 15px;"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    
                    # Allow updating/overwriting the PDF
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("⚙️ Update Legal Notice PDF"):
                        uploaded_file = st.file_uploader("Upload new PDF to replace the current Legal Notice", type=["pdf"], key="update_pdf")
                        if uploaded_file is not None:
                            pdf_path.parent.mkdir(exist_ok=True)
                            pdf_path.write_bytes(uploaded_file.getvalue())
                            st.success("✅ Legal Notice PDF updated successfully!")
                            time.sleep(1)
                            st.rerun()
                    
                except Exception as e:
                    st.error(f"Error loading Legal Notice PDF: {e}")
            else:
                st.error("Legal Notice PDF not found.")
                
                # Uploader to set the PDF
                st.markdown("---")
                st.markdown("#### 📤 Upload Legal Notice PDF")
                uploaded_file = st.file_uploader("Choose a PDF file to set as the official Legal Notice", type=["pdf"], key="upload_pdf")
                if uploaded_file is not None:
                    try:
                        pdf_path.parent.mkdir(exist_ok=True)
                        pdf_path.write_bytes(uploaded_file.getvalue())
                        st.success("✅ Legal Notice PDF uploaded successfully!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save uploaded PDF: {e}")
        elif app_mode == "⚙️ Admin Dashboard":
            st.markdown("### ⚙️ Security & System Administration Dashboard")
            st.write("Manage registered platform users, view document upload metadata, inspect system audit logs, and access live application logs.")
            
            headers = {"Authorization": f"Bearer {st.session_state.auth_token}"}
            
            tab_users, tab_logs, tab_docs, tab_system_logs = st.tabs([
                "👤 User Management",
                "📋 Security Audit Logs",
                "📄 Uploaded Documents",
                "📝 Application Logs"
            ])
            
            with tab_users:
                st.markdown("#### 👥 Registered System Users")
                try:
                    res_u = requests.get(f"{API_BASE_URL}/api/admin/users", headers=headers, timeout=15)
                    if res_u.status_code == 200:
                        import pandas as pd
                        users_data = res_u.json()
                        df_users = pd.DataFrame(users_data)
                        if not df_users.empty:
                            st.dataframe(df_users, use_container_width=True)
                            
                            st.markdown("---")
                            st.markdown("##### ⚙️ Manage User Role / Delete User")
                            col_u1, col_u2, col_u3 = st.columns([1, 2, 2])
                            with col_u1:
                                target_user_id = st.number_input("Target User ID", min_value=1, step=1, key="admin_user_id_input")
                            with col_u2:
                                new_role = st.selectbox("Assign New Role", ["User", "Admin"], key="admin_user_role_select")
                                update_role_btn = st.button("🔄 Update Role", type="primary", use_container_width=True)
                            with col_u3:
                                st.write("") # spacing
                                delete_user_btn = st.button("🚨 Delete User Account", type="secondary", use_container_width=True)
                                
                            if update_role_btn:
                                res_role = requests.post(
                                    f"{API_BASE_URL}/api/admin/users/{target_user_id}/role",
                                    json={"role": new_role},
                                    headers=headers,
                                    timeout=15
                                )
                                if res_role.status_code == 200:
                                    st.success("✅ User role updated successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed to update role: {res_role.json().get('detail', 'Unknown error')}")
                                    
                            if delete_user_btn:
                                res_del = requests.post(
                                    f"{API_BASE_URL}/api/admin/users/{target_user_id}/delete",
                                    headers=headers,
                                    timeout=15
                                )
                                if res_del.status_code == 200:
                                    st.success("✅ User deleted successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed to delete user: {res_del.json().get('detail', 'Unknown error')}")
                        else:
                            st.info("No registered users found.")
                    else:
                        st.error(f"❌ Failed to load users: HTTP {res_u.status_code}")
                except Exception as e:
                    st.error(f"❌ Error communicating with admin service: {e}")
                    
            with tab_logs:
                st.markdown("#### 📋 Security Audit Logs")
                try:
                    res_l = requests.get(f"{API_BASE_URL}/api/admin/logs", headers=headers, timeout=15)
                    if res_l.status_code == 200:
                        import pandas as pd
                        logs_data = res_l.json()
                        df_logs = pd.DataFrame(logs_data)
                        if not df_logs.empty:
                            st.dataframe(df_logs, use_container_width=True)
                        else:
                            st.info("No audit logs recorded yet.")
                    else:
                        st.error(f"❌ Failed to load audit logs: HTTP {res_l.status_code}")
                except Exception as e:
                    st.error(f"❌ Error loading logs: {e}")
                    
            with tab_docs:
                st.markdown("#### 📄 Uploaded Documents Metadata (AES-256 Encrypted Storage)")
                try:
                    res_d = requests.get(f"{API_BASE_URL}/api/admin/documents", headers=headers, timeout=15)
                    if res_d.status_code == 200:
                        import pandas as pd
                        docs_data = res_d.json()
                        df_docs = pd.DataFrame(docs_data)
                        if not df_docs.empty:
                            st.dataframe(df_docs, use_container_width=True)
                        else:
                            st.info("No documents uploaded yet.")
                    else:
                        st.error(f"❌ Failed to load documents: HTTP {res_d.status_code}")
                except Exception as e:
                    st.error(f"❌ Error loading documents: {e}")
                    
            with tab_system_logs:
                st.markdown("#### 📝 Live Backend Application Logs")
                log_file_path = "backend.log"
                import os
                if os.path.exists(log_file_path):
                    try:
                        with open(log_file_path, "r", encoding="utf-8") as lf:
                            # Read last 100 lines
                            lines = lf.readlines()
                            last_lines = lines[-100:]
                            st.code("".join(last_lines), language="log")
                    except Exception as e:
                        st.error(f"Failed to read log file: {e}")
                else:
                    st.info("Backend log file (backend.log) not found in workspace.")
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; margin-top: 20px; padding-bottom: 20px;'>
            <small style='color: #718096;'>
                Indian Legal Advisor | Powered by InLegalBERT + FAISS + Qwen3 | 
                <a href='https://github.com' style='color: #d4af37; text-decoration: none;'>GitHub</a>
            </small>
        </div>
        """, unsafe_allow_html=True)
        pass

    render_main_app()
