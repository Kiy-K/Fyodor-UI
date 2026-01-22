import os
import sys

# Add the project root to the Python path
# This is necessary to resolve relative imports when running the app directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from medgemma_triage import auth
from medgemma_triage import ui

# --- Page Configuration ---
st.set_page_config(
    page_title="MCP Doctor Dashboard",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Styling ---
ui.setup_styles()

# --- Authentication Gatekeeper ---
auth.seed_admin_user() # Ensure the admin user exists for the demo

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    # --- Login Form ---
    st.title("👨‍⚕️ MCP Doctor Dashboard Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if auth.verify_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password.")

    st.stop() # --- IMPORTANT: Stop execution if not authenticated ---

# --- Main Dashboard Application ---
# This code runs ONLY if st.session_state.authenticated is True

from medgemma_triage import mcp_client
from medgemma_triage import utils
from groq import Groq

def run_consultation(patient_id, notes, files):
    """Orchestrates the entire consultation process, including the agentic workflow."""

    with st.spinner("Compiling patient data..."):
        history = mcp_client.call_backend_tool("get_patient_history", {"patient_id": patient_id}) or "No patient history found."
        doc_texts, image_files = utils.process_uploaded_files(files)

        initial_prompt = f"""
        **Patient ID:** {patient_id}
        **Physician's Notes:** {notes}
        **Patient History:** {history}
        **Uploaded Document Contents:** {doc_texts}
        **Instructions:**
        Based on all available data, provide a clinical analysis. If you need more information, use the [SEARCH: query] tool.
        Structure your final response with the headings: ### Executive Summary, ### Detailed Reasoning, and ### Sources & Search Data.
        """
        st.session_state.raw_data = initial_prompt

    try:
        client = Groq(api_key=utils.get_secret("GROQ_API_KEY"))
        messages = [{"role": "user", "content": initial_prompt}]

        for _ in range(3): # Allow up to 3 turns for the agentic loop
            with st.spinner("AI is analyzing..."):
                response_stream = client.chat.completions.create(
                    messages=messages,
                    model="llama3-70b-8192",
                    temperature=0.2,
                    stream=True
                )

                full_response = ""
                placeholder = st.empty()
                for chunk in response_stream:
                    full_response += chunk.choices[0].delta.content or ""
                    placeholder.markdown(full_response + "...")

            search_query = utils.extract_search_command(full_response)
            if search_query:
                messages.append({"role": "assistant", "content": full_response})
                with st.spinner(f"Searching for: {search_query}..."):
                    search_results = mcp_client.call_backend_tool("search_medical_web", {"query": search_query})
                messages.append({"role": "user", "content": f"Search results for '{search_query}':\n{search_results}"})
            else:
                break # No search command found, so we're done.

        # Parse and display the final response
        parsed_response = utils.parse_dashboard_response(full_response)
        st.session_state.summary = parsed_response["summary"]
        st.session_state.reasoning = parsed_response["reasoning"]
        st.session_state.summary_placeholder.markdown(st.session_state.summary)
        st.session_state.reasoning_placeholder.markdown(st.session_state.reasoning)

        # Save the log
        mcp_client.call_backend_tool("save_consultation_log", {"patient_id": patient_id, "log_entry": full_response})
        st.success("Consultation complete and log saved.")

    except Exception as e:
        st.error(f"An error occurred during the AI analysis: {e}")

def main_dashboard():
    """Renders the main dashboard UI and orchestrates the logic."""

    # --- Session State Initialization ---
    if "summary" not in st.session_state:
        st.session_state.summary = "Waiting for analysis..."
    if "reasoning" not in st.session_state:
        st.session_state.reasoning = "Waiting for analysis..."
    if "raw_data" not in st.session_state:
        st.session_state.raw_data = "Input data will be displayed here."

    # --- Sidebar ---
    with st.sidebar:
        st.title("MCP Dashboard")
        st.write(f"Welcome, **Dr. {st.session_state.username}**")
        st.markdown("---")

        mode = st.radio("Select Mode", ["👨‍⚕️ Doctor Mode", "🤒 Patient Mode"])

        if st.button("Logout"):
            # Clear all session state on logout
            for key in st.session_state.keys():
                del st.session_state[key]
            st.session_state.authenticated = False
            st.rerun()

    # --- Main Content (40/60 Split) ---
    st.title("Clinical Intelligence Dashboard")

    col1, col2 = st.columns([2, 3])

    with col1:
        # --- Input Zone ---
        st.header("Control Panel")
        patient_id = st.text_input("Patient ID", placeholder="e.g., Patient-001")

        physician_notes = st.text_area(
            "Physician Notes / Clinical Context",
            height=200,
            placeholder="Enter patient history, current observations, and specific questions..."
        )

        uploaded_files = st.file_uploader(
            "Upload Clinical Documents (PDF, DOCX, Images)",
            accept_multiple_files=True
        )

        if st.button("Run Consult", use_container_width=True, type="primary"):
            if not patient_id and not physician_notes and not uploaded_files:
                st.warning("Please provide a Patient ID, notes, or at least one document.")
            else:
                run_consultation(patient_id, physician_notes, uploaded_files)

    with col2:
        # --- Intelligence Zone ---
        st.header("Analysis & Results")

        tab1, tab2, tab3 = st.tabs(["📊 Executive Summary", "🧠 Reasoning Trace", "🗃️ Raw Data"])

        with tab1:
            st.markdown("### High-Level Assessment")
            st.session_state.summary_placeholder = st.empty()
            st.session_state.summary_placeholder.markdown(st.session_state.summary)

        with tab2:
            st.markdown("### Step-by-Step Logic")
            st.session_state.reasoning_placeholder = st.empty()
            st.session_state.reasoning_placeholder.markdown(st.session_state.reasoning)

        with tab3:
            st.markdown("### Supporting Data & Citations")
            st.text_area("Compiled Input Data", st.session_state.raw_data, height=400, disabled=True)

if __name__ == "__main__":
    main_dashboard()
