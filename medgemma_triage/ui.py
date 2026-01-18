import streamlit as st

def setup_styles():
    """
    Injects custom CSS for the application.
    """
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
        .unknown { background-color: #95a5a6; }

        div.stButton > button:first-child {
            background-color: #00796B;
            color: white;
        }

        /* Sticky Footer Styles */
        /* Add padding to the bottom of the main block so messages aren't hidden */
        .block-container {
            padding-bottom: 150px;
        }
        /* Style the fixed bottom container */
        .fixed-bottom {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: #F5F7F8; /* Matches app background or white */
            border-top: 1px solid #ddd;
            padding: 1rem 1rem 2rem 1rem;
            z-index: 999;
        }
        /* Hide the default Streamlit footer */
        footer {visibility: hidden;}

        </style>
    """, unsafe_allow_html=True)

def render_clean_response(parsed_response):
    """
    Renders the parsed response:
    1. Thought in an expander (optional, based on requirement to show only final assessment).
       - User requirement: "Strip out... show ONLY the final medical assessment, not the internal reasoning log."
       - Implication: Do NOT show the thought expander.
    2. Content as main text.
    3. Triage card if JSON data exists.
    """
    thought = parsed_response.get("thought")
    content = parsed_response.get("content")
    data = parsed_response.get("data")
    is_json = parsed_response.get("is_json")

    # 1. Thought Process - HIDDEN per requirement
    # if thought:
    #     with st.expander("🧠 Clinical Reasoning"):
    #         st.markdown(thought)

    # 2. Main Content
    if content:
        st.markdown(content)

    # 3. Triage Data (Card)
    if is_json and isinstance(data, dict):
        level = data.get("triage_level", "UNKNOWN").upper()
        rationale = data.get("clinical_rationale", "No rationale provided.")
        actions = data.get("recommended_actions", [])

        color_class = "unknown"
        if level == "EMERGENCY":
            color_class = "emergency"
        elif level == "URGENT":
            color_class = "urgent"
        elif level == "STABLE":
            color_class = "stable"

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
    elif not is_json and not content and not thought:
        # Fallback if everything is empty
        pass
