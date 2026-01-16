import json
import re
import base64

def encode_image_to_base64(uploaded_file):
    """Encodes an uploaded Streamlit file to a Base64 string."""
    if uploaded_file is None:
        return None
    try:
        bytes_data = uploaded_file.getvalue()
        return base64.b64encode(bytes_data).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

def parse_medgemma_response(raw_text: str) -> dict:
    """
    Robust parser for MedGemma responses.
    Supports <think>...</think>, <unused94>thought...<unused95>.

    Extracts:
    1. 'thought' (CoT)
    2. 'json_data' (Structured data like NEWS2 scores, if present in JSON block)
    3. 'markdown_report' (The main body of the response, usually SOAP report)
    """
    # 1. Extract Thought
    thought_match = re.search(
        r'(<unused94>thought|<think>)(.*?)(<unused95>|</think>)',
        raw_text,
        re.DOTALL
    )
    thought = thought_match.group(2).strip() if thought_match else ""
    
    # Remove thought block from text to get the rest
    clean_text = re.sub(
        r'(<unused94>thought|<think>).*?(<unused95>|</think>)',
        '',
        raw_text,
        flags=re.DOTALL
    ).strip()
    
    # 2. Extract JSON (if any)
    json_data = None
    # Look for a JSON block ```json ... ```
    json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', clean_text, re.DOTALL)
    if json_block_match:
        try:
            json_data = json.loads(json_block_match.group(1))
        except:
            pass

    if not json_data:
        # Fallback: try to find the first braces block that parses
        try:
            # We look for the LAST brace block if multiple exist,
            # often the JSON summary is at the end.
            # But let's stick to simple first match for now or robust search.
            candidates = re.findall(r'\{.*?\}', clean_text, re.DOTALL)
            for candidate in reversed(candidates):
                try:
                    data = json.loads(candidate)
                    if "news2_score" in data or "triage_level" in data:
                        json_data = data
                        break
                except:
                    continue
        except (json.JSONDecodeError, Exception):
            pass

    # 3. The rest is Markdown Report
    # We remove the JSON block if it was found via ```json```
    markdown_report = clean_text
    if json_block_match:
        markdown_report = clean_text.replace(json_block_match.group(0), "").strip()

    # Also optionally remove raw JSON if it was just trailing at the end without blocks?
    # For now, we leave it if it's not in a block, to avoid accidental deletion of report text.

    return {
        "thought": thought,
        "json_data": json_data,
        "markdown_report": markdown_report
    }
