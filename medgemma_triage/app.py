import streamlit as st
import os
import asyncio
import json
from dotenv import load_dotenv
from upstash_redis import Redis
import utils

# 1. Setup & Config
load_dotenv()

st.set_page_config(
    page_title="MedGemma Triage 🏥",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }
    .stButton > button { border-radius: 8px; font-weight: 600; }
    div[data-testid="stExpander"] div[role="button"] p { font-size: 1rem; font-weight: 600; }

    /* Thought Block Styling */
    .thought-block {
        background-color: #F1F5F9;
        border-left: 4px solid #64748B;
        padding: 10px;
        border-radius: 4px;
        margin-bottom: 10px;
        font-family: monospace;
        font-size: 0.9em;
        color: #475569;
    }
</style>
""", unsafe_allow_html=True)

# 2. Redis Connection
# Load from secrets or env
UPSTASH_URL = utils.get_config("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = utils.get_config("UPSTASH_REDIS_REST_TOKEN")

@st.cache_resource
def get_redis_client():
    if UPSTASH_URL and UPSTASH_TOKEN:
        try:
            return Redis(url=UPSTASH_URL, token=UPSTASH_TOKEN)
        except Exception:
            return None
    return None

redis_client = get_redis_client()

# 3. Sidebar: Patient Vitals & Triage
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

    # Reactive Triage Call
    # Calls backend tool every time inputs change
    triage_args = {
        "hr": int(hr), "sbp": int(sbp), "rr": int(rr),
        "temp": float(temp), "spo2": int(spo2),
        "consciousness": consciousness, "oxygen": bool(o2_supp)
    }
    
    # Call backend synchronously
    # We catch errors to avoid breaking the UI if backend is down
    try:
        triage_resp = utils.call_mcp_tool("triage_patient", triage_args)
        # Expecting JSON string or direct result
        try:
            if isinstance(triage_resp, str):
                # Try to extract JSON if it's wrapped in text
                json_match = utils.JSON_PATTERN.search(triage_resp)
                if json_match:
                    triage_data = json.loads(json_match.group(0))
                else:
                     triage_data = json.loads(triage_resp)
            else:
                triage_data = triage_resp
        except:
            triage_data = {"score": "?", "risk": "Error parsing result"}
    except Exception as e:
        triage_data = {"score": "Err", "risk": "Connection Fail"}

    st.divider()
    score = triage_data.get("score", "N/A")
    risk = triage_data.get("risk", "Unknown")

    # Determine color based on risk (simple heuristic for UI)
    delta_color = "normal"
    if str(risk).lower() in ["high", "medium"]:
        delta_color = "inverse"

    st.metric("NEWS2 Score", score, delta=risk, delta_color=delta_color)

    # Redis Chart
    st.subheader("History")
    chart_data = []
    if redis_client:
        try:
            # Fetch last 20 scores
            history = redis_client.lrange("patient:news2:history", -20, -1)
            if history:
                chart_data = [float(x) for x in history]
        except Exception:
            pass

    if not chart_data:
        chart_data = [0] * 5 # Fallback empty chart

    st.line_chart(chart_data, height=150)

# 4. Main Layout: Split Screen
col_left, col_right = st.columns([1, 1])

# --- LEFT COLUMN: INTERACTION ---
with col_left:
    st.header("Interaction Console")

    # Inputs
    st.subheader("Clinical Dictation")
    audio_input = st.audio_input("Record Voice Note")

    st.subheader("Medical Imaging")
    uploaded_file = st.file_uploader("Upload X-Ray", type=['png', 'jpg', 'jpeg'])

    if uploaded_file:
        st.image(uploaded_file, caption="X-Ray Preview", use_column_width=True)

    st.markdown("---")
    run_btn = st.button("🚀 Run Full Triage & Analysis", type="primary", use_container_width=True)

    # Status / Orchestration Visualization
    status_container = st.empty()

    # Chat Interface (Bottom of Left Column)
    st.markdown("### 💬 Consultant Chat")

    # Initialize Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display Chat Messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Ask follow-up questions..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get Context from Report
        report_context = ""
        if "final_report" in st.session_state and st.session_state.final_report:
             report_context = st.session_state.final_report.get("markdown_report", "")

        # Call Chat Tool
        with st.chat_message("assistant"):
            with st.spinner("Consulting..."):
                try:
                    # Prepare history as string or list
                    chat_history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ]

                    response = utils.call_mcp_tool(
                        "chat_with_consultant",
                        {
                            "query": prompt,
                            "context_context": report_context, # Distinct arg name
                            "history": json.dumps(chat_history) # Passing as JSON string to be safe
                        }
                    )
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Chat Error: {e}")


# --- RIGHT COLUMN: CLINICAL ARTIFACT ---
with col_right:
    # State Management
    if "report_state" not in st.session_state:
        st.session_state.report_state = "standby"
    if "final_report" not in st.session_state:
        st.session_state.final_report = {}

    # Display Logic
    if st.session_state.report_state == "standby":
        with st.container(border=True):
             st.markdown("#### Waiting for Triage Data...")
             st.info("Upload inputs on the left and click Run to generate the SOAP note.")
             # Static image or table placeholder
             st.markdown("##### NEWS2 Protocol Reference")
             st.table({
                 "Score": ["0-4", "5-6", "7+"],
                 "Risk": ["Low", "Medium", "High"],
                 "Response": ["Ward-based", "Urgent Review", "Emergency Call"]
             })

    elif st.session_state.report_state == "processing":
        with st.container(border=True):
             st.spinner("Generating Clinical Artifact...")
             st.markdown("*Analysis in progress...*")

    elif st.session_state.report_state == "ready":
        data = st.session_state.final_report

        # Metadata Expander
        with st.expander("📄 Patient Metadata (OCR)", expanded=False):
             # Try to find metadata in the gathered results if stored,
             # or generic info. Since we don't persist the raw metadata in session_state
             # cleanly in my previous thought, let's fix that in the logic below.
             if "metadata_result" in st.session_state:
                 st.code(st.session_state.metadata_result)
             else:
                 st.write("No metadata extracted.")

        # Thoughts Visualization
        if data.get("thought"):
            with st.expander("🧠 Clinical Reasoning (Chain-of-Thought)", expanded=False):
                 st.markdown(f"<div class='thought-block'>{data['thought']}</div>", unsafe_allow_html=True)

        # The Paper Record
        with st.container(border=True):
            st.markdown("### 📋 SOAP NOTE")
            st.markdown(data.get("markdown_report", "No report generated."))

            st.download_button(
                "📥 Download Record",
                data.get("markdown_report", ""),
                file_name="soap_note.md"
            )


# --- ORCHESTRATION LOGIC ---
if run_btn:
    st.session_state.report_state = "processing"

    # We use a status container in the left col to show progress
    with status_container.status("🚀 AI Agent Orchestrating...", expanded=True) as status:

        # 1. Gather Inputs (Parallel)
        status.write("⚡ Gathering Clinical Data (Audio + Vision)...")
        try:
            # Run async gathering
            # We pass the file objects directly. utils will handle encoding.
            results = asyncio.run(utils.gather_analysis_inputs(audio_input, uploaded_file))

            audio_transcript = results.get("audio", "")
            image_analysis = results.get("image_analysis", "")
            image_metadata = results.get("image_metadata", "")

            # Save metadata for display
            st.session_state.metadata_result = image_metadata

            status.write("✅ Data Transcribed & Analyzed.")
        except Exception as e:
            st.error(f"Input Processing Failed: {e}")
            st.stop()

        # 2. Prepare Context for MedGemma
        status.write("🔄 Aggregating Context...")

        # Get latest vitals from sidebar variables (they are available in scope)
        vitals_context = json.dumps(triage_data)

        full_context = f"""
        VITALS DATA (NEWS2):
        {vitals_context}

        AUDIO TRANSCRIPT:
        {audio_transcript}

        VISUAL FINDINGS:
        {image_analysis}

        EXTRACTED METADATA:
        {image_metadata}
        """

        # 3. Consult MedGemma
        status.write("🧠 Consulting MedGemma Specialist...")
        try:
            report_raw = utils.call_mcp_tool(
                "consult_medgemma",
                {
                    "query": "Generate a full clinical SOAP note based on this patient data.",
                    "context_data": full_context
                }
            )

            # Parse response
            parsed_report = utils.parse_medgemma_response(report_raw)
            st.session_state.final_report = parsed_report
            st.session_state.report_state = "ready"

            status.update(label="✅ Analysis Complete", state="complete", expanded=False)

        except Exception as e:
            status.update(label="❌ Consultation Failed", state="error")
            st.error(f"Error: {e}")

    # Rerun to update the Right Column UI
    st.rerun()
