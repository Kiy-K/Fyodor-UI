import streamlit as st
import prompts
from jules_brain import ask_fastmcp

st.set_page_config(page_title=prompts.APP_TITLE, page_icon=prompts.APP_ICON)

st.title(f"{prompts.APP_ICON} {prompts.APP_TITLE}")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("How can I help you?"):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get response
    with st.chat_message("assistant"):
        with st.spinner(prompts.CONNECTING_MSG):
            response_obj = ask_fastmcp(prompt)

        # Determine how to display response based on its type
        # The return type of the custom client.responses.create is unknown,
        # so we try to extract content or default to string representation.
        content = str(response_obj)

        # Attempt to make it cleaner if it's a simple object with a 'content' or 'output' attribute
        # (This is speculative based on common patterns, but fallback is safe)
        if hasattr(response_obj, 'output'):
            content = response_obj.output
        elif hasattr(response_obj, 'content'):
            content = response_obj.content
        elif isinstance(response_obj, dict) and 'output' in response_obj:
            content = response_obj['output']

        st.markdown(content)
        st.session_state.messages.append({"role": "assistant", "content": content})
