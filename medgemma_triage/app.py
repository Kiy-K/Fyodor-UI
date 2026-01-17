import streamlit as st
from backend import get_response
from PIL import Image

st.set_page_config(page_title="MedGemma Vision Assistant", page_icon="👁️")

st.title("👁️ MedGemma Vision Assistant")
st.caption("Powered by Modal SGLang Server")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar: Image Upload
with st.sidebar:
    st.header("Multimodal Input")
    uploaded_image = st.file_uploader("Upload Medical Image (X-Ray, MRI, etc.)", type=["png", "jpg", "jpeg"])

    if uploaded_image:
        # Display preview
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Image", use_container_width=True)

# Main Chat Interface
# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # If there was an image associated with this message, we could display it,
        # but for now we just show the preview in sidebar for the *current* turn.
        # Ideally, we should store image in history if we want persistent display,
        # but requirement is simple chat interface.

# User Input
if prompt := st.chat_input("Ask about the image or describe symptoms..."):
    # 1. Display User Message
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_image:
             st.info("Attached Image")

    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Get Response
    with st.chat_message("assistant"):
        # Pass text and the uploaded file object to backend
        response_stream = get_response(prompt, image_file=uploaded_image)

        # Stream the result
        full_response = st.write_stream(response_stream)

    # 3. Save Assistant Message
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Optional: Clear uploaded image after send?
    # Usually better to keep it if user has follow up questions about same image.
    # We leave it as is.
