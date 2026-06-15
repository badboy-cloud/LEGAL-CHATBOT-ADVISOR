"""
Indian Legal Advisor - Streamlit Frontend
Professional UI for legal query analysis and FIR document processing.
"""

import streamlit as st
import requests
import time
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Indian Legal Advisor",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Header
st.markdown("<h1 class='title-text'>⚖️ Indian Legal Advisor</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-text'>Intelligent Legal Assistant Powered by InLegalBERT + FAISS + Qwen3</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ System Settings")
    domain_threshold = st.slider(
        "Domain Classifier Threshold",
        min_value=0.1,
        max_value=0.9,
        value=0.3,
        step=0.05,
        help="Higher values make legal validation stricter. Lower values allow broader matching."
    )
    
    st.markdown("---")
    st.markdown("### 📋 Supported Legal Domains")
    domains = {
        "⚖️ Criminal Law": "IPC/BNS violations, physical offense, theft, assault",
        "👨‍👩‍👧 Family Law": "Divorce, maintenance, domestic violence, custody",
        "🏠 Property Law": "Landlord-tenant disputes, boundary issues, transfer",
        "📝 Contract Law": "Breach, service agreements, commercial pacts",
        "🛒 Consumer Law": "Deficient services, product liability, fraud",
        "👷 Labour & Employment": "Overtime, wrongful termination, disputes",
        "🔐 Cyber Law": "Hacking, data theft, online fraud, identity theft",
        "💰 Defamation": "Written or spoken false statements damaging reputation",
        "📜 Constitutional Law": "Fundamental rights violation, writ petitions",
        "🏛️ Civil Law": "General civil disputes, recovery of dues, injunctions"
    }
    for dom, desc in domains.items():
        st.markdown(f"**{dom}**  \n<small style='color:#718096;'>{desc}</small>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🏛️ Disclaimer")
    st.warning("This platform is an AI advisory tool for educational and preliminary support. It does not constitute formal legal advice. Always consult a qualified lawyer.")

# Top-level Tabs
main_tab1, main_tab2 = st.tabs(["💡 Legal Query Advisory", "📄 FIR Document Analysis"])

# --- TAB 1: LEGAL QUERY ADVISORY ---
with main_tab1:
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
        with st.spinner("🔄 Running legal classification, precedent retrieval, and Qwen3 reasoning..."):
            try:
                start_time = time.time()
                response = requests.post(
                    f"{API_BASE_URL}/api/analyze",
                    json={
                        "query": query_input,
                        "domain_threshold": domain_threshold
                    },
                    timeout=API_TIMEOUT
                )
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.query_results = {
                        "data": data,
                        "elapsed": elapsed
                    }
                else:
                    st.error(f"❌ API returned status code {response.status_code}")
                    try:
                        st.write(response.json())
                    except:
                        st.write(response.text)
            except Exception as e:
                st.error("❌ Connection Failed. Unable to communicate with the Legal Advisor API.")
                st.info("Please ensure that the FastAPI backend server is running on port 8000. If you are running locally, start it with: `python src/main.py`")

    # Render Query Results
    if st.session_state.query_results:
        res = st.session_state.query_results["data"]
        elapsed = st.session_state.query_results["elapsed"]
        
        if res.get("status") == "error":
            st.error(f"⚠️ Rejection: {res.get('message')}")
        else:
            # Stats & Performance Row
            topic_info = res.get("topic", {})
            st.markdown(f"""
            <div style='margin-bottom: 15px;'>
                <span class='metric-badge'>📌 Topic: {topic_info.get('name', 'N/A').replace('_', ' ').title()} ({topic_info.get('confidence', 0)*100:.1f}%)</span>
                <span class='metric-badge'>⏱️ Time taken: {elapsed:.2f}s</span>
                <span class='metric-badge'>📚 Cases found: {len(res.get('precedents', []))}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Sub-tabs for detailed view
            q_tab1, q_tab2, q_tab3, q_tab4 = st.tabs(["💡 Legal Advice", "📖 Applicable Statutes", "📚 Similar Precedents", "📊 Raw API Response"])
            
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
                    
            with q_tab4:
                st.subheader("JSON Response Details")
                st.json(res)


# --- TAB 2: FIR DOCUMENT ANALYSIS ---
with main_tab2:
    st.markdown("### 📄 Upload First Information Report (FIR)")
    st.write("Upload a scanned image (JPG, JPEG, PNG) or digital PDF copy of the FIR document to extract details and analyze legal implications.")
    
    uploaded_file = st.file_uploader(
        "Choose an FIR file...",
        type=["pdf", "jpg", "jpeg", "png"],
        help="Supported: PDF, JPG, JPEG, PNG"
    )
    
    col1, col2 = st.columns([5, 1])
    with col2:
        analyze_fir_btn = st.button("🔍 Analyze FIR Document", type="primary", use_container_width=True)
        
    if analyze_fir_btn and uploaded_file is not None:
        with st.spinner("🔄 Uploading file, extracting text via OCR/PDF parser, structuring metadata, and generating report..."):
            try:
                start_time = time.time()
                
                # Format multipart file upload
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/api/analyze-fir",
                    files=files,
                    timeout=API_TIMEOUT
                )
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.fir_results = {
                        "data": data,
                        "elapsed": elapsed
                    }
                else:
                    st.error(f"❌ API returned status code {response.status_code}")
                    try:
                        st.write(response.json())
                    except:
                        st.write(response.text)
            except Exception as e:
                st.error("❌ Connection/Processing Failed. Unable to analyze the FIR document.")
                st.info("Please verify that the FastAPI backend server is running on port 8000 and that Tesseract OCR/pypdf dependencies are correctly configured.")

    # Render FIR Results
    if st.session_state.fir_results:
        f_res = st.session_state.fir_results["data"]
        elapsed = st.session_state.fir_results["elapsed"]
        
        perf = f_res.get("performance", {})
        # Display warning if partial success due to LLM failure/timeout
        if f_res.get("status") == "partial_success":
            stopped_stage = perf.get('current_stage', 'Unknown')
            st.warning(f"⚠️ **Processing Stopped at Stage:** `{stopped_stage}`. Qwen generated no final answer. Showing fallback legal analysis.")
        
        # Risk Badge Class selection
        risk_lvl = f_res.get("risk_level", "Medium")
        if risk_lvl == "High":
            risk_badge = f"<span class='risk-high'>⚠️ Risk: {risk_lvl}</span>"
        elif risk_lvl == "Low":
            risk_badge = f"<span class='risk-low'>✅ Risk: {risk_lvl}</span>"
        else:
            risk_badge = f"<span class='risk-medium'>⚠️ Risk: {risk_lvl}</span>"
            
        topic_str = f_res.get("topic", "N/A").replace('_', ' ').title()
        
        # Metadata Header Row
        st.markdown(f"""
        <div style='margin-bottom: 20px;'>
            <span class='metric-badge'>📁 FIR No: {f_res.get('fir_number', 'N/A')}</span>
            <span class='metric-badge'>🏢 PS: {f_res.get('police_station', 'N/A')}</span>
            <span class='metric-badge'>📌 Category: {topic_str}</span>
            {risk_badge}
            <span class='metric-badge'>⏱️ Total Time: {elapsed:.2f}s</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Display Stage Timings
        perf = f_res.get("performance", {})
        if perf:
            ocr_t = perf.get('ocr_time_seconds', 0.0)
            meta_t = perf.get('regex_extraction_time_seconds', 0.0) or perf.get('metadata_extraction_time_seconds', 0.0) or 0.0
            class_t = perf.get('classification_time_seconds', 0.0)
            stat_t = perf.get('statute_prediction_time_seconds', 0.0)
            ret_t = perf.get('retrieval_time_seconds', 0.0)
            qwen_t = perf.get('generation_time_seconds', 0.0)
            tot_t = perf.get('total_pipeline_time_seconds', 0.0) or perf.get('total_time_seconds', 0.0) or 0.0
            
            # Helper to get color code
            def get_color(t, fast=1.0, medium=5.0):
                if t <= fast:
                    return "#00cc66" # green
                elif t <= medium:
                    return "#ffa500" # orange
                else:
                    return "#ff4b4b" # red
            
            st.markdown(f"""
            <div style="margin-bottom: 20px;">
                <h4 style="color:#d4af37; margin-top:0; margin-bottom:12px; font-size:16px;">⏱️ Performance Dashboard</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px;">
                    <div style="background: #161a23; padding: 10px; border: 1px solid #2d3748; border-radius: 8px; text-align: center;">
                        <div style="font-size: 10px; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px;">OCR Extraction</div>
                        <div style="font-size: 16px; font-weight: 700; color: {get_color(ocr_t, 0.5, 2.0)}; margin-top: 4px;">{ocr_t:.2f}s</div>
                    </div>
                    <div style="background: #161a23; padding: 10px; border: 1px solid #2d3748; border-radius: 8px; text-align: center;">
                        <div style="font-size: 10px; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px;">Metadata Regex</div>
                        <div style="font-size: 16px; font-weight: 700; color: {get_color(meta_t, 0.1, 0.5)}; margin-top: 4px;">{meta_t:.2f}s</div>
                    </div>
                    <div style="background: #161a23; padding: 10px; border: 1px solid #2d3748; border-radius: 8px; text-align: center;">
                        <div style="font-size: 10px; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px;">Classification</div>
                        <div style="font-size: 16px; font-weight: 700; color: {get_color(class_t, 0.5, 2.0)}; margin-top: 4px;">{class_t:.2f}s</div>
                    </div>
                    <div style="background: #161a23; padding: 10px; border: 1px solid #2d3748; border-radius: 8px; text-align: center;">
                        <div style="font-size: 10px; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px;">Statute Predict</div>
                        <div style="font-size: 16px; font-weight: 700; color: {get_color(stat_t, 0.1, 0.5)}; margin-top: 4px;">{stat_t:.2f}s</div>
                    </div>
                    <div style="background: #161a23; padding: 10px; border: 1px solid #2d3748; border-radius: 8px; text-align: center;">
                        <div style="font-size: 10px; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px;">FAISS Retrieval</div>
                        <div style="font-size: 16px; font-weight: 700; color: {get_color(ret_t, 0.5, 2.0)}; margin-top: 4px;">{ret_t:.2f}s</div>
                    </div>
                    <div style="background: #161a23; padding: 10px; border: 1px solid #2d3748; border-radius: 8px; text-align: center;">
                        <div style="font-size: 10px; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px;">Qwen3:8B Gen</div>
                        <div style="font-size: 16px; font-weight: 700; color: {get_color(qwen_t, 30.0, 120.0)}; margin-top: 4px;">{qwen_t:.2f}s</div>
                    </div>
                    <div style="background: rgba(212, 175, 55, 0.05); padding: 10px; border: 1px solid rgba(212, 175, 55, 0.3); border-radius: 8px; text-align: center;">
                        <div style="font-size: 10px; color: #d4af37; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Total Pipeline</div>
                        <div style="font-size: 16px; font-weight: 700; color: #d4af37; margin-top: 4px;">{tot_t:.2f}s</div>
                    </div>
                </div>
                <div style="margin-top: 8px; font-size: 12px; color: #a0aec0;">
                    • <b>Completed Stage Status:</b> <span style="color: #d4af37;">{perf.get('current_stage', 'Completed')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Layout columns for FIR Details
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class='info-card'>
                <h4 style='margin-top:0; color:#d4af37;'>👥 Involved Parties</h4>
                <p><b>Complainant / Informant:</b> {f_res.get('complainant', 'N/A')}</p>
                <p><b>Accused Person(s):</b> {f_res.get('accused', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            # Join statutes lists
            sections_list = f_res.get("sections", [])
            sections_str = ", ".join(sections_list) if sections_list else "No sections identified"
            st.markdown(f"""
            <div class='info-card'>
                <h4 style='margin-top:0; color:#d4af37;'>⚖️ Cited Legal Sections</h4>
                <p><b>Statutes / Code Provisions:</b></p>
                <p style='font-size: 16px; font-weight:600; color:#e2e8f0;'>{sections_str}</p>
            </div>
            """, unsafe_allow_html=True)
            
        # Tabs for Analysis, Precedents, Extracted Text, JSON
        f_tab1, f_tab2, f_tab3, f_tab4 = st.tabs([
            "💡 AI Legal Analysis Report", 
            "📚 Related Precedents", 
            "📄 Extracted Document Text", 
            "📊 Raw API Response"
        ])
        
        with f_tab1:
            st.markdown("### 💡 AI Legal Advisory Report")
            st.markdown(f_res.get("legal_advice", "No advisory generated."))
            
        with f_tab2:
            st.markdown("### 📚 Similar Precedents (FAISS Retrieval)")
            precedents = f_res.get("precedents", [])
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
                
        with f_tab3:
            st.markdown("### 📄 Raw Extracted Text from Document")
            st.text_area(
                "Extracted Text content:",
                value=f_res.get("extracted_text", "No text extracted."),
                height=350,
                disabled=True
            )
            
        with f_tab4:
            st.subheader("JSON Response Details")
            st.json(f_res)

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