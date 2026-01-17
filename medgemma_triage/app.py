import streamlit as st
import os
import time
import base64
from openai import OpenAI
from dotenv import load_dotenv
import utils
import tools
import prompts

# 1. Configuration & Setup
load_dotenv()

st.set_page_config(
    page_title="MedGemma Triage Pro",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Medical Look
st.markdown("""
    <style>
    .reportview-container {
        background: #F5F7F8;
    }
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        color: #37474F;
    }
    .stApp {
        background-color: #F5F7F8;
    }
    .triage-card {
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    .emergency { background-color: #e74c3c; }
    .urgent { background-color: #e67e22; }
    .stable { background-color: #27ae60; }

    div.stButton > button:first-child {
        background-color: #00796B;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Sidebar & State
with st.sidebar:
    st.image("https://img.icons8.com/color/96/caduceus.png", width=80)
    st.title("MedGemma Pro")
    st.markdown("---")

    st.subheader("System Status")

    # Check Modal Config (Brain)
    modal_url = os.getenv("MODAL_API_URL")
    if modal_url:
        st.success(f"Brain: Connected (Modal)")
    else:
        st.error("Brain: Missing Configuration")

    # Check Modal ASR Config (Ear)
    modal_asr_url = os.getenv("MODAL_ASR_URL")
    if modal_asr_url:
        st.success(f"Ear: Connected (Modal)")
    else:
        st.error("Ear: Missing Configuration")

    # Check MCP Config
    mcp_url = os.getenv("MCP_SERVER_URL")
    if mcp_url:
        st.success(f"MCP: {mcp_url}")
    else:
        st.warning("MCP: Not Configured")

    st.markdown("---")
    st.subheader("Model Settings")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2)

    if st.button("List Available Tools"):
        with st.spinner("Fetching tools..."):
            tool_list = tools.list_tools()
            st.json(tool_list)

    show_history = st.toggle("Show Patient History", value=False)

    if st.button("Reset Session"):
        st.session_state.messages = []
        st.session_state.draft_text = ""
        st.rerun()

    with st.sidebar.expander("📤 Legacy Upload"):
        uploaded_image = st.file_uploader("Upload Medical Image (X-ray, MRI, etc.)", type=['jpg', 'jpeg', 'png'])
        uploaded_audio = st.file_uploader("Upload Medical Recording (Patient voice, doctor notes)", type=['wav', 'mp3', 'm4a'])

# Initialize State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "draft_text" not in st.session_state:
    st.session_state.draft_text = ""
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

# 3. Main Interface
st.markdown("<h1 class='main-header'>🏥 MedGemma Triage System</h1>", unsafe_allow_html=True)
st.caption("AI-Powered Clinical Decision Support • v2.0 (Modal + FastMCP)")

# Display Chat History
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            if isinstance(msg["content"], str):
                st.markdown(msg["content"])
            elif isinstance(msg["content"], list):
                for item in msg["content"]:
                    if item["type"] == "text":
                        st.markdown(item["text"])
                    elif item["type"] == "image_url":
                        st.image(item["image_url"]["url"])
            else:
                st.write(msg["content"])

# 4. Helper Function: Run Triage Logic
def run_triage_engine(user_text, image_obj=None):
    """Executes the full ReAct loop for a given text and optional image."""

    # 1. Prepare Message Content (Multimodal)
    message_content = user_text

    if image_obj:
        img_bytes = image_obj.read()
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        message_content = [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
        ]
        st.toast("Sending multimodal data to MedGemma 27B...", icon="🚀")

    # Add User Message to History
    st.session_state.messages.append({"role": "user", "content": message_content})
    with st.chat_message("user"):
        st.markdown(user_text)
        if image_obj:
            image_obj.seek(0)
            st.image(image_obj)

    # Prepare Context for Model
    context_messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}] + st.session_state.messages

    with st.chat_message("assistant"):
        placeholder = st.empty()
        status_container = st.status("Initializing Medical Brain... (May be slow on cold start)", expanded=True)

        try:
            # --- ReAct LOOP ---
            max_turns = 5
            final_response_text = ""

            for turn in range(max_turns):
                # Call Model
                try:
                    status_container.write(f"AI Brain: Modal MedGemma 27B (Turn {turn+1})...")
                    response_text = call_model(context_messages)
                except Exception as e:
                    status_container.update(label="System Warning", state="error")
                    st.error(str(e))
                    st.stop()

                # Check for Search Command
                search_query = utils.extract_search_command(response_text)

                if search_query:
                    status_container.markdown(f"**Tool Call:** `[SEARCH: {search_query}]`")
                    tool_result = tools.search_pubmed(search_query)
                    status_container.write("Tool result received.")
                    context_messages.append({"role": "assistant", "content": response_text})
                    context_messages.append({"role": "user", "content": f"TOOL_RESULT for '{search_query}':\n{tool_result}"})

                else:
                    final_response_text = response_text
                    status_container.update(label="Diagnosis Complete", state="complete", expanded=False)
                    break

            # --- DISPLAY RESULTS ---
            parsed = utils.parse_medgemma_response(final_response_text)

            if parsed["thought"]:
                with st.expander("🧠 Clinical Reasoning Process"):
                    st.markdown(parsed["thought"])

            if parsed["is_json"] and isinstance(parsed["data"], dict):
                data = parsed["data"]
                level = data.get("triage_level", "UNKNOWN").upper()
                rationale = data.get("clinical_rationale", "No rationale provided.")
                actions = data.get("recommended_actions", [])

                color_class = "stable"
                if level == "EMERGENCY":
                    color_class = "emergency"
                elif level == "URGENT":
                    color_class = "urgent"

                st.markdown(f"""
                <div class="triage-card {color_class}">
                    <h2>{level}</h2>
                    <p><strong>Rationale:</strong> {rationale}</p>
                </div>
                """, unsafe_allow_html=True)

                if actions:
                    st.markdown("### 📋 Recommended Actions")
                    for action in actions:
                        st.markdown(f"- {action}")
            else:
                st.warning("Raw Output (Could not parse JSON):")
                st.markdown(parsed["data"])

            st.session_state.messages.append({"role": "assistant", "content": final_response_text})

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

def call_model(messages):
    """Calls the remote model via OpenAI client."""
    client = OpenAI(
        base_url=os.getenv("MODAL_API_URL"),
        api_key=os.getenv("MODAL_API_KEY", "dummy")
    )
    try:
        response = client.chat.completions.create(
            model="google/medgemma-27b-it",
            messages=messages,
            temperature=temperature,
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg or "timeout" in error_msg.lower() or "connection error" in error_msg.lower():
            raise Exception("System is warming up (Cold Start). Please wait 30-60 seconds and try again.")
        raise e

# 5. Live Audio & Legacy Upload Handling
st.markdown("---")
st.subheader("🎤 Live Voice Triage")

# Audio Inputs
col1, col2 = st.columns([1, 4])
with col1:
    audio_value = st.audio_input("🎤 Speak Symptoms (MedASR Optimized)")

# Logic to handle new audio inputs (Live or Uploaded)
new_audio_bytes = None
source_name = ""

# Prioritize Live Audio if present, then Sidebar Upload
if audio_value:
    new_audio_bytes = audio_value.read()
    source_name = "Live Recording"
elif uploaded_audio:
    uploaded_audio.seek(0)
    new_audio_bytes = uploaded_audio.read()
    source_name = "Uploaded File"

# Check if we need to transcribe (only if audio changed)
if new_audio_bytes:
    # Hash check to avoid re-transcribing same audio on every rerun
    current_hash = hash(new_audio_bytes)
    if st.session_state.last_processed_audio != current_hash:
        with st.status(f"👂 Converting speech to medical text ({source_name})...") as status:
            transcription = tools.transcribe_audio(new_audio_bytes)

            # Update Draft
            if st.session_state.draft_text:
                 st.session_state.draft_text += f"\n\n[TRANSCRIPTION: {transcription}]"
            else:
                 st.session_state.draft_text = f"[TRANSCRIPTION: {transcription}]"

            st.session_state.last_processed_audio = current_hash
            status.write("Done!")
            st.rerun()

# Draft Area
draft = st.text_area("📝 Review Transcription / Draft Notes",
                     value=st.session_state.draft_text,
                     height=150,
                     key="draft_input")

# Sync text area changes back to session state
if draft != st.session_state.draft_text:
    st.session_state.draft_text = draft

if st.button("🚀 Send to MedGemma", type="primary"):
    if st.session_state.draft_text.strip():
        # Execute Triage
        run_triage_engine(st.session_state.draft_text, uploaded_image)
        # Clear Draft
        st.session_state.draft_text = ""
        st.rerun()
    else:
        st.warning("Please record audio or type notes first.")

# Standard Chat Input (Bottom)
chat_input_val = st.chat_input("Or type a quick message here...")
if chat_input_val:
    run_triage_engine(chat_input_val, uploaded_image)
