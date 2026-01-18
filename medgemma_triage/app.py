import streamlit as st
import os
import time
import base64
from openai import OpenAI
from dotenv import load_dotenv
import utils
import tools
import prompts
import ui
from utils import get_secret

# 1. Configuration & Setup
load_dotenv()

st.set_page_config(
    page_title="MedGemma Triage Pro",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Medical Look & Sticky Footer
ui.setup_styles()

# 2. Sidebar & State
with st.sidebar:
    st.image("https://img.icons8.com/color/96/caduceus.png", width=80)
    st.title("MedGemma Pro")
    st.markdown("---")

    st.subheader("System Status")

    # Check Modal Config (Brain)
    modal_url = get_secret("MODAL_API_URL")
    if modal_url:
        st.success(f"Brain: Connected (Modal)")
    else:
        st.error("Brain: Missing Configuration")

    # Check Groq ASR Config (Ear)
    groq_api_key = get_secret("GROQ_API_KEY")
    if groq_api_key:
        st.success(f"Ear: Connected (Groq Whisper)")
    else:
        st.error("Ear: Missing Configuration")

    # Check MCP Config
    mcp_url = get_secret("MCP_SERVER_URL")
    if mcp_url:
        st.success(f"MCP: {mcp_url}")
    else:
        st.warning("MCP: Not Configured")

    st.markdown("---")
    st.subheader("Triage Engine")
    engine_choice = st.radio(
        "Select Model",
        ["Expert (Modal 27B)", "Fast (Groq 70B)"],
        index=0
    )

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
        st.session_state.user_draft = ""
        st.rerun()

    with st.sidebar.expander("📤 Legacy Upload"):
        uploaded_image = st.file_uploader("Upload Medical Image (X-ray, MRI, etc.)", type=['jpg', 'jpeg', 'png'])
        uploaded_audio = st.file_uploader("Upload Medical Recording (Patient voice, doctor notes)", type=['wav', 'mp3', 'm4a'])

# Initialize State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_draft" not in st.session_state:
    st.session_state.user_draft = ""
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None

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

def call_model(messages):
    """Calls the remote model via OpenAI client."""
    client = OpenAI(
        base_url=get_secret("MODAL_API_URL"),
        api_key=get_secret("MODAL_API_KEY", "dummy")
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
        st.toast("Sending multimodal data...", icon="🚀")

    # Add User Message to History
    st.session_state.messages.append({"role": "user", "content": message_content})
    with st.chat_message("user"):
        st.markdown(user_text)
        if image_obj:
            image_obj.seek(0)
            st.image(image_obj)

    # Prepare Context for Model
    context_messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}] + st.session_state.messages

    # Determine Engine
    use_fast_engine = "Fast" in engine_choice
    source_type = "fast" if use_fast_engine else "expert"
    engine_name = "Groq Llama-3.3-70B" if use_fast_engine else "Modal MedGemma 27B"

    with st.chat_message("assistant"):
        placeholder = st.empty()
        status_container = st.status(f"Initializing {engine_name}...", expanded=True)

        try:
            # --- ReAct LOOP ---
            # Note: Fast engine might not follow strict ReAct loop with tools as robustly,
            # but we'll try to keep the loop structure for search calls if supported.
            max_turns = 5
            final_response_text = ""

            for turn in range(max_turns):
                # Call Model
                try:
                    status_container.write(f"AI Brain: {engine_name} (Turn {turn+1})...")
                    if use_fast_engine:
                        response_text = tools.call_fast_triage(context_messages)
                    else:
                        response_text = call_model(context_messages)
                except Exception as e:
                    status_container.update(label="System Warning", state="error")
                    st.error(str(e))
                    # Stop execution if model call fails
                    return

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
            parsed = utils.parse_medgemma_response(final_response_text, source=source_type)

            # Use UI helper to render
            ui.render_clean_response(parsed)

            # Store ONLY the clean content (stripped of thoughts) or the full raw?
            # Usually we store what we showed or the raw response.
            # Storing raw allows context to be preserved, but for display we want clean.
            # Given the strict requirement "Show ONLY final assessment", we should probably
            # ensure that when this is rendered from history, it is also clean.
            # But render_clean_response handles that.
            # We append the full raw response to history so the model has context for next turn.
            st.session_state.messages.append({"role": "assistant", "content": final_response_text})

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

# --- FLOATING INPUT BAR ---
# Logic: Place this code at the VERY END of your script (after displaying chat history)
with st.container():
    # This container simulates the sticky footer
    st.markdown('<div class="fixed-bottom">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 4, 1])

    with col1:
        # AUDIO INPUT (Compact)
        audio_val = st.audio_input("Record", label_visibility="collapsed")

    with col2:
        # TEXT INPUT (Populated by Audio or Manual Typing)
        # Logic: If audio_val changes, update session_state.user_draft
        if audio_val:
            # Transcribe only if it's new audio
            if st.session_state.get("last_audio_id") != audio_val.id:
                try:
                    # Read bytes from audio value
                    audio_bytes = audio_val.read()
                    transcribed_text = tools.transcribe_audio(audio_bytes)

                    # Append to existing draft or replace? Usually replace or append.
                    # Let's append if there is existing text, or just replace?
                    # "Populated by Audio" usually implies filling it.
                    # But if user typed something, we don't want to lose it.
                    if st.session_state.user_draft:
                        st.session_state.user_draft += f" {transcribed_text}"
                    else:
                        st.session_state.user_draft = transcribed_text

                    st.session_state.last_audio_id = audio_val.id
                except Exception as e:
                    st.error(f"Audio Error: {e}")

        # The Text Area acts as the main input
        # Note: 'key' is crucial for state syncing. We use a separate key for the widget
        # and sync it to user_draft manually if needed, or just rely on the key being same as session state variable?
        # Streamlit allows key="user_draft" to bind directly to st.session_state.user_draft.
        # This is the cleanest way.
        user_input = st.text_area(
            "Message MedGemma...",
            value=st.session_state.user_draft,
            height=68, # Minimal height
            label_visibility="collapsed",
            key="chat_box_input" # Using a distinct key to avoid conflicts if we manipulate state manually above
        )

        # Sync back to state if user types manually
        if user_input != st.session_state.user_draft:
             st.session_state.user_draft = user_input

    with col3:
        # SEND BUTTON
        if st.button("🚀 Send", use_container_width=True, type="primary"):
            if st.session_state.user_draft.strip():
                # Trigger the standard "Send Message" logic here
                run_triage_engine(st.session_state.user_draft, uploaded_image)
                # Clear input
                st.session_state.user_draft = ""
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

