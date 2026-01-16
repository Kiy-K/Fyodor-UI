import streamlit as st
import os
import json
import httpx
from dotenv import load_dotenv
from upstash_redis import Redis
import tools
import utils

# 1. Setup & Config
load_dotenv()

st.set_page_config(
    page_title="MedGemma Triage 🏥",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Medical Theme
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }
    h1, h2, h3 { color: #0F172A; font-weight: 700; }
    [data-testid="stMetricValue"] { color: #0EA5E9; font-size: 2rem; }
    .stButton > button { background-color: #0EA5E9; color: white; border-radius: 8px; font-weight: 600; }
    .stButton > button:hover { background-color: #0284C7; }
</style>
""", unsafe_allow_html=True)

# 2. Redis Connection
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

@st.cache_resource
def get_redis_client():
    if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
        try:
            return Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
        except Exception:
            return None
    return None

redis_client = get_redis_client()

# 3. Helper Functions (Cached)

@st.cache_data(show_spinner=False, ttl=60)
def get_triage_score(hr, sbp, rr, temp, spo2, consciousness, oxygen):
    """Calls triage_patient tool to get NEWS2 score."""
    args = {
        "hr": int(hr), "sbp": int(sbp), "rr": int(rr),
        "temp": float(temp), "spo2": int(spo2),
        "consciousness": consciousness, "oxygen": bool(oxygen)
    }
    # For demo/reliability if MCP is down, we might want a fallback,
    # but requirement is to use the tool.
    try:
        # Call MCP Tool
        # Result is expected to be a JSON string like '{"score": 7, ...}'
        result_str = tools.call_mcp_tool("triage_patient", args)

        # Try to parse JSON
        if isinstance(result_str, str):
            # Sometimes tools return extra text, try to find JSON
            match = utils.JSON_PATTERN.search(result_str)
            if match:
                return json.loads(match.group(0))
            # Fallback if it's just a number or clean JSON
            try:
                return json.loads(result_str)
            except:
                return {"score": "?", "error": "Parse Error"}
        return result_str
    except Exception as e:
        return {"score": "?", "error": str(e)}

# 4. Sidebar: Patient Vitals
with st.sidebar:
    st.image("https://img.icons8.com/color/96/caduceus.png", width=64)
    st.title("Patient Vitals")
    
    with st.container():
        c1, c2 = st.columns(2)
        hr = c1.number_input("HR (bpm)", 0, 300, 85)
        sbp = c2.number_input("Sys BP", 0, 300, 110)

        c3, c4 = st.columns(2)
        rr = c3.number_input("RR (bpm)", 0, 60, 18)
        temp = c4.number_input("Temp (°C)", 20.0, 45.0, 37.2, step=0.1)

        spo2 = st.number_input("SpO2 (%)", 0, 100, 96)
        consciousness = st.selectbox("Consciousness", ["Alert", "Voice", "Pain", "Unresponsive"])
        o2_supp = st.checkbox("Oxygen Support?")

    # Reactive Calculation
    triage_result = get_triage_score(hr, sbp, rr, temp, spo2, consciousness, o2_supp)
    
    # Display Metric
    st.divider()
    score = triage_result.get("score", "N/A")
    risk = triage_result.get("risk", "Unknown")

    st.metric("NEWS2 Score", score, delta=risk, delta_color="inverse")

    # Live Chart from Redis
    st.subheader("History")
    chart_data = [0, 1, 0, 2, 5] # Default mock
    if redis_client:
        try:
            # Fetch last 10 scores
            history = redis_client.lrange("patient:demo:news2", -10, -1)
            if history:
                # Convert bytes/strings to int
                chart_data = [int(float(x)) for x in history]
        except Exception:
            pass # Keep mock

    st.line_chart(chart_data, height=150)

# 5. Main Layout
col_left, col_right = st.columns([1, 1])

# --- LEFT COLUMN: INPUTS & ORCHESTRATION ---
with col_left:
    st.header("Examination Console")

    # Audio
    st.subheader("1. Clinical Dictation")
    audio_input = st.audio_input("Record Voice Note")

    # Vision
    st.subheader("2. Medical Imaging")
    uploaded_file = st.file_uploader("Upload X-Ray", type=['png', 'jpg', 'jpeg'])

    if uploaded_file:
        st.image(uploaded_file, use_column_width=True, caption="Preview")

    st.markdown("---")
    run_btn = st.button("🚀 Run Full Triage & Analysis", type="primary", use_container_width=True)

# --- RIGHT COLUMN: OUTPUT ---
with col_right:
    # State Management
    if "report_state" not in st.session_state:
        st.session_state.report_state = "standby" # standby, processing, ready
    if "final_report" not in st.session_state:
        st.session_state.final_report = {}

    if st.session_state.report_state == "standby":
        st.info("👋 Ready for consultation. Upload data and click Run.")
        # Reference Card Placeholder
        st.markdown("""
        #### NEWS2 Reference
        | Score | Risk | Response |
        |-------|------|----------|
        | 0-4 | Low | Ward-based response |
        | 5-6 | Medium | Key threshold for urgent response |
        | 7+ | High | Emergency response |
        """)

    elif st.session_state.report_state == "processing":
         with st.status("🤖 MedGemma Agent Working...", expanded=True) as status:
             st.write("Initializing...")
             # Logic will happen in the button callback, but UI updates here
             # if we used a rerun. Since we do logic in the button callback,
             # this state might be transient or we update the status container directly there.

    elif st.session_state.report_state == "ready":
        data = st.session_state.final_report

        # Thoughts
        with st.expander("🧠 Agent Thoughts (Chain-of-Thought)", expanded=False):
            st.markdown(data.get("thought", "No thoughts captured."))

        # Report
        with st.container(border=True):
            st.markdown("### 📋 OFFICIAL SOAP NOTE")
            st.markdown(data.get("markdown_report", ""))

            # Download
            st.download_button(
                "📥 Download Report",
                data.get("markdown_report", ""),
                file_name="soap_report.md"
            )


# --- LOGIC: ORCHESTRATION ---
if run_btn:
    # Update State (Visual only, execution is sync here)
    st.session_state.report_state = "processing"

    # We need a placeholder in the right column to show progress LIVE
    # because the script is running top-to-bottom.
    # We can write to col_right directly.

    with col_right:
        # Clear previous content
        st.empty()

        with st.status("🤖 MedGemma Orchestration...", expanded=True) as status:

            # Context Accumulator
            context_parts = []

            # Step 1: Vitals (Immediate)
            status.write("📊 analyzing vitals...")
            # We already have `triage_result` from sidebar
            vitals_json = json.dumps(triage_result)
            context_parts.append(f"VITALS ANALYSIS:\n{vitals_json}")

            # Step 2: Audio (Parallel-ish)
            if audio_input:
                status.write("👂 Transcribing audio...")
                try:
                    b64_audio = utils.encode_to_base64(audio_input)
                    transcript = tools.call_mcp_tool("transcribe_medical_audio", {"audio_base64": b64_audio})
                    context_parts.append(f"AUDIO TRANSCRIPT:\n{transcript}")
                    status.write("✅ Audio transcribed.")
                except Exception as e:
                    status.write(f"❌ Audio Error: {e}")

            # Step 3: Vision
            if uploaded_file:
                status.write("👁️ Scanning X-Ray (Multi-scale)...")
                try:
                    b64_image = utils.encode_to_base64(uploaded_file)
                    vision_analysis = tools.call_mcp_tool("analyze_xray_multiscale", {"image_base64": b64_image})

                    # Metadata
                    status.write("📄 Extracting Metadata...")
                    meta = tools.call_mcp_tool("extract_xray_metadata", {"image_base64": b64_image})

                    context_parts.append(f"IMAGE ANALYSIS:\n{vision_analysis}")
                    context_parts.append(f"IMAGE METADATA:\n{meta}")
                    status.write("✅ Image analyzed.")
                except Exception as e:
                    status.write(f"❌ Vision Error: {e}")

            # Step 4: Synthesis & Consult
            status.write("🧠 Consulting MedGemma (Generating SOAP)...")
            full_context = "\n\n".join(context_parts)

            try:
                # Call consult_medgemma
                # Note: The tool expects 'query' and 'context_data'
                response_text = tools.call_mcp_tool(
                    "consult_medgemma",
                    {
                        "query": "Generate a professional SOAP report based on this context.",
                        "context_data": full_context
                    }
                )

                # Step 5: Save History
                status.write("💾 Saving Record...")
                tools.call_mcp_tool("manage_patient_history", {"action": "save", "content": response_text})
                
                # Parse
                parsed = utils.parse_medgemma_response(response_text)
                st.session_state.final_report = parsed
                st.session_state.report_state = "ready"
                
                status.update(label="✅ Complete", state="complete", expanded=False)
                
            except Exception as e:
                status.update(label="❌ Analysis Failed", state="error")
                st.error(f"MedGemma Error: {e}")
                
    # Rerun to show the "ready" state in the main flow
    st.rerun()
