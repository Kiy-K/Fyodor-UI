import openai
import base64
from PIL import Image
import io

# Configuration
BASE_URL = "https://khoitruong071510--medgemma-hackathon-medgemmaserver-open-bfc148.modal.run/v1"
API_KEY = "EMPTY"
MODEL_NAME = "default"

client = openai.Client(
    base_url=BASE_URL,
    api_key=API_KEY
)

def encode_image_to_base64(image_file):
    """
    Encodes a PIL Image or UploadedFile to a base64 string.
    """
    if image_file is None:
        return None

    # Check if it's already bytes-like or a file-like object
    try:
        # If it's a streamlit UploadedFile, .read() gives bytes
        # We need to reset cursor if it was read before, but usually we handle it once
        if hasattr(image_file, "getvalue"):
             bytes_data = image_file.getvalue()
        elif hasattr(image_file, "read"):
             bytes_data = image_file.read()
        else:
             # Assume it is a PIL image or similar
             buffered = io.BytesIO()
             image_file.save(buffered, format="JPEG")
             bytes_data = buffered.getvalue()

        return base64.b64encode(bytes_data).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

def get_response(user_text, image_file=None):
    """
    Generates a response from the Modal SGLang backend.
    Supports text-only or multimodal (image + text) inputs.
    Returns an iterable (stream) of response chunks.
    """
    messages = []

    if image_file:
        base64_image = encode_image_to_base64(image_file)

        if base64_image:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        else:
            # Fallback if image encoding failed
             messages = [{"role": "user", "content": f"[Image Upload Failed] {user_text}"}]
    else:
        messages = [{"role": "user", "content": user_text}]

    try:
        stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            stream=True
        )
        return stream
    except Exception as e:
        # Return a simple iterator with the error message
        return [f"Error communicating with backend: {str(e)}"]
