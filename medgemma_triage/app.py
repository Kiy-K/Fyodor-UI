import streamlit as st
import prompts
from mcp_client import query_jules_mcp

# Setup
st.set_page_config(
    page_title=prompts.APP_TITLE,
    page_icon=prompts.APP_ICON,
)

st.title(f"{prompts.APP_ICON} {prompts.APP_TITLE}")
st.markdown(prompts.DISCLAIMER)

# Input
user_query = st.text_input("Describe symptoms or ask a medical question:", placeholder="e.g. 45yo male with chest pain...")

# Button
if st.button("Ask Jules"):
    if not user_query.strip():
        st.warning("Please enter a query.")
    else:
        status = st.status(prompts.CONNECTING_STATUS)
        try:
            # Call backend
            response = query_jules_mcp(user_query)

            # Update Status
            status.update(label="Complete", state="complete", expanded=False)

            # Display Result
            st.success("Response Received")
            st.markdown(response)

        except Exception as e:
            status.update(label="Error", state="error")
            st.error(f"Failed to connect to backend: {str(e)}")
