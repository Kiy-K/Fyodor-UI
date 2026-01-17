import streamlit as st
from jules_bridge import get_agent_response

st.set_page_config(page_title="Jules (FastMCP Responses API)", page_icon="🤖")

st.title("🤖 Jules (FastMCP Responses API)")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask Jules..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get response
    with st.chat_message("assistant"):
        with st.spinner("Calling v1/responses..."):
            resp = get_agent_response(prompt)

        st.subheader("Raw Response Object Inspection")
        st.write(resp)

        # Attempt to display content nicely if possible
        content = str(resp)
        if hasattr(resp, 'output_text'):
            content = resp.output_text
        elif hasattr(resp, 'content'):
            content = resp.content
        elif isinstance(resp, dict) and 'output' in resp:
            content = resp['output']

        # Only add to history if we found a string representation that looks like a message
        # Otherwise we just leave the raw inspection above for this refactor.
        # But to be helpful, we append the stringified version.
        st.session_state.messages.append({"role": "assistant", "content": content})
