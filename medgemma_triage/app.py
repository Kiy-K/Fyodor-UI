import streamlit as st
import json
import asyncio
from upstash_redis import Redis
import utils

# 1. Setup & Config
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
    .stChatInput { position: fixed; bottom: 0; }
</style>
""", unsafe_allow_html=True)

# 2. Redis Connection
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

# 3. Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "generated_report" not in st.session_state:
    st.session_state.generated_report = ""

# 4. Sidebar: Vitals
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

    # Simple Redis Chart (Mock if empty)
    st.divider()
    st.subheader("History")
    chart_data = [0] * 5
    if redis_client:
        try:
            history = redis_client.lrange("patient:news2:history", -20, -1)
            if history:
                chart_data = [float(x) for x in history]
        except:
            pass
    st.line_chart(chart_data, height=100)

# 5. Main Layout
col_left, col_right = st.columns([1, 1])

# --- LEFT COLUMN: Interaction ---
with col_left:
    st.header("Interaction Console")

    # Inputs
    with st.expander("📁 Clinical Assets", expanded=True):
        audio_input = st.audio_input("Record Voice Note")
        uploaded_file = st.file_uploader("Upload X-Ray", type=['png', 'jpg', 'jpeg'])

    # Chat Interface
    st.markdown("### 💬 Consultant Chat")

    # Render History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    prompt = st.chat_input("Enter clinical query or click Run Triage...")
    run_triage = st.button("🚀 Run Triage & Analysis", type="primary", use_container_width=True)

    # Trigger Logic
    input_text = None
    if run_triage:
        input_text = "Please perform a full triage analysis, transcribe the audio, analyze the image, and generate a SOAP report."
    elif prompt:
        input_text = prompt

    if input_text:
        # 1. User Message to UI
        st.session_state.messages.append({"role": "user", "content": input_text})
        with st.chat_message("user"):
            st.markdown(input_text)

        # 2. Agent Execution
        with st.chat_message("assistant"):
            # Context Bundle
            context_files = {
                "audio": audio_input,
                "image": uploaded_file
            }

            # Helper for Vitals Context Injection if needed in future
            # For now, we assume the user enters them manually in the sidebar
            # or the agent asks for them. But to be helpful, let's inject vitals
            # into the prompt if it's the first run.
            vitals_str = f"Current Vitals: HR={hr}, BP={sbp}, RR={rr}, Temp={temp}, SpO2={spo2}, Consciousness={consciousness}, Oxygen={o2_supp}"

            full_input = f"{input_text}\n\n[System Note: {vitals_str}]"

            # Streamlit Status Container
            status_box = st.status("Agent Working...", expanded=True)
            response_placeholder = st.empty()
            full_response = ""

            # Run Loop
            generator = utils.run_agent_loop(
                user_input=full_input,
                context_files=context_files,
                chat_history=st.session_state.messages[:-1] # Exclude the one we just added to display
            )

            try:
                for event_type, content in generator:
                    if event_type == "status":
                        status_box.write(f"ℹ️ {content}")
                    elif event_type == "tool":
                        status_box.write(f"🛠️ {content}")
                    elif event_type == "tool_result":
                        status_box.write(f"✅ {content}")
                    elif event_type == "content":
                        full_response = content
                        response_placeholder.markdown(full_response)
                    elif event_type == "error":
                        status_box.update(label="❌ Error", state="error")
                        st.error(content)

                status_box.update(label="✅ Complete", state="complete", expanded=False)

                # Save to history
                if full_response:
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

                    # Detect SOAP Report for Right Column
                    if "SOAP" in full_response or "Subjective" in full_response:
                        st.session_state.generated_report = full_response

            except Exception as e:
                status_box.update(label="❌ Critical Failure", state="error")
                st.error(f"System Error: {e}")

# --- RIGHT COLUMN: Artifact ---
with col_right:
    if st.session_state.generated_report:
        with st.container(border=True):
            st.markdown("### 📋 Formal Clinical Record")
            st.markdown(st.session_state.generated_report)
            st.download_button(
                "📥 Download Record",
                st.session_state.generated_report,
                file_name="soap_note.md"
            )
    else:
        with st.container(border=True):
            st.markdown("#### Waiting for Triage Data...")
            st.info("Upload inputs on the left and start the triage process.")
            st.markdown("##### NEWS2 Protocol Reference")
            st.table({
                "Score": ["0-4", "5-6", "7+"],
                "Risk": ["Low", "Medium", "High"],
                "Response": ["Ward-based", "Urgent Review", "Emergency Call"]
            })
