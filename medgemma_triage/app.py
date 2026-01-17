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
        background: #f0f2f6;
    }
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        color: #2c3e50;
    }
    .stApp {
        background-color: #FFFFFF;
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
        background-color: #008080;
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

    if st.button("Reset Session"):
        st.session_state.messages = []
        st.rerun()

    with st.sidebar.expander("📤 Media Upload"):
        uploaded_image = st.file_uploader("Upload Medical Image (X-ray, MRI, etc.)", type=['jpg', 'jpeg', 'png'])
        uploaded_audio = st.file_uploader("Upload Medical Recording (Patient voice, doctor notes)", type=['wav', 'mp3', 'm4a'])

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

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
                # Handle structured display for past messages if needed
                st.write(msg["content"])

# 4. Logic & ReAct Loop
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
            max_tokens=2048
        )
        return response.choices[0].message.content
    except Exception as e:
        # Cold start handling
        error_msg = str(e)
        if "503" in error_msg or "timeout" in error_msg.lower() or "connection error" in error_msg.lower():
            raise Exception("System is warming up (Cold Start). Please wait 30-60 seconds and try again.")
        raise e

user_input = st.chat_input("Describe patient symptoms (e.g., '45M with chest pain')...")

if user_input:
    # 1. Handle Audio
    if uploaded_audio:
        with st.status("Initializing Medical Engines (Ear & Brain)... This may take a minute on first run.") as status:
            status.write("AI Ear: Modal MedASR")
            audio_bytes = uploaded_audio.read()
            transcription = tools.transcribe_audio(audio_bytes)
            user_input += f"\n\n[TRANSCRIPTION: {transcription}]"
            st.write("Transcription added.")

    # 2. Prepare Message Content (Multimodal)
    message_content = user_input

    if uploaded_image:
        img_bytes = uploaded_image.read()
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        message_content = [
            {"type": "text", "text": user_input},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
        ]
        st.toast("Sending multimodal data to MedGemma 27B...", icon="🚀")

    # Add User Message
    st.session_state.messages.append({"role": "user", "content": message_content})
    with st.chat_message("user"):
        st.markdown(user_input)
        if uploaded_image:
            uploaded_image.seek(0)
            st.image(uploaded_image)

    # Prepare Context
    context_messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}] + st.session_state.messages

    with st.chat_message("assistant"):
        placeholder = st.empty()
        status_container = st.status("Initializing Medical Engines (Ear & Brain)... This may take a minute on first run.", expanded=True)

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
                    # Show tool usage in UI
                    status_container.markdown(f"**Tool Call:** `[SEARCH: {search_query}]`")

                    # Execute Tool
                    tool_result = tools.search_pubmed(search_query)
                    status_container.write("Tool result received.")

                    # Append interaction to context
                    # Note: We represent the assistant's call and the tool's result in the message history
                    # for the next turn.
                    context_messages.append({"role": "assistant", "content": response_text})
                    context_messages.append({"role": "user", "content": f"TOOL_RESULT for '{search_query}':\n{tool_result}"})

                else:
                    # No tool call -> Final Response
                    final_response_text = response_text
                    status_container.update(label="Diagnosis Complete", state="complete", expanded=False)
                    break

            # --- DISPLAY RESULTS ---
            parsed = utils.parse_medgemma_response(final_response_text)

            # 1. Show Thoughts
            if parsed["thought"]:
                with st.expander("🧠 Clinical Reasoning Process"):
                    st.markdown(parsed["thought"])

            # 2. Show Triage Card
            if parsed["is_json"] and isinstance(parsed["data"], dict):
                data = parsed["data"]
                level = data.get("triage_level", "UNKNOWN").upper()
                rationale = data.get("clinical_rationale", "No rationale provided.")
                actions = data.get("recommended_actions", [])

                # Determine Color
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
                # Fallback if not valid JSON
                st.warning("Raw Output (Could not parse JSON):")
                st.markdown(parsed["data"])

            # Add to history
            st.session_state.messages.append({"role": "assistant", "content": final_response_text})

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
