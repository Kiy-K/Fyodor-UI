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
        div.stButton > button:first-child {
            background-color: #00796B;
            color: white;
            border: none;
        }
        div.stButton > button:hover {
            background-color: #004D40;
            color: white;
        }
        /* Hide the default Streamlit footer */
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
