import json
import re
import base64
import io

# Pre-compile regex patterns for efficiency
THOUGHT_PATTERN = re.compile(
    r'(<unused94>thought|<think>)(.*?)(<unused95>|</think>)',
    re.DOTALL
)
JSON_PATTERN = re.compile(r'\{.*\}', re.DOTALL)


def parse_medgemma_response(raw_text: str) -> dict:
    """
    Robust parser for MedGemma responses.
    Supports <think>...</think>, <unused94>thought...<unused95>.

    Extracts:
    1. 'thought' (CoT)
    2. 'json_data' (Structured data like NEWS2 scores, if present in JSON block)
    3. 'markdown_report' (The main body of the response, usually SOAP report)
    """
    if not raw_text:
        return {"thought": "", "json_data": None, "markdown_report": ""}

    # 1. Extract Thought (support both <think> and <unused94>)
    thought_match = THOUGHT_PATTERN.search(raw_text)
    thought = thought_match.group(2).strip() if thought_match else ""
    
    # Remove thought block from text to get the report content
    clean_text = THOUGHT_PATTERN.sub('', raw_text).strip()
    
    # 2. Extract JSON (if any)
    json_data = None
    try:
        json_match = JSON_PATTERN.search(clean_text)
        if json_match:
            json_str = json_match.group(0)
            json_data = json.loads(json_str)
            # Optionally remove JSON from report if it's meant to be hidden?
            # For now, we leave it in the text or maybe the user wants it hidden.
            # Usually SOAP report is text. If JSON is the structured output, maybe we keep it separate.
            # Let's assume the report is the clean text.
    except (json.JSONDecodeError, Exception):
        pass

    return {
        "thought": thought,
        "json_data": json_data,
        "markdown_report": clean_text
    }

def encode_to_base64(file_obj) -> str:
    """Encodes a file-like object to Base64 string."""
    if file_obj is None:
        return None
    try:
        # Check if it has read attribute
        if hasattr(file_obj, 'read'):
            file_bytes = file_obj.read()
            # Try to reset cursor if possible
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
        else:
            file_bytes = file_obj

        return base64.b64encode(file_bytes).decode('utf-8')
    except Exception as e:
        print(f"Error encoding to base64: {e}")
        return None
