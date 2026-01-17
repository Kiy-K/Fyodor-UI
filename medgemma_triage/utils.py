import re
import json

def extract_search_command(text):
    """
    Extracts the [SEARCH: query] command from the text.
    Returns the query string if found, otherwise None.
    """
    if not text:
        return None
    match = re.search(r"\[SEARCH:\s*(.*?)\]", text)
    if match:
        return match.group(1).strip()
    return None

def parse_medgemma_response(text):
    """
    Parses the model response to extract:
    1. Thought process (inside <think>...</think> or <unused94>thought... or just text before JSON)
    2. JSON data (first valid JSON object found)

    Returns a dict: {"thought": str, "data": dict or str, "is_json": bool}
    """
    if not text:
        return {"thought": "", "data": {}, "is_json": False}

    thought = ""
    json_data = {}
    is_json = False

    # 1. Extract Thought
    # Try <think> tags first
    think_match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
    if think_match:
        thought = think_match.group(1).strip()
    else:
        # Try <unused94>thought pattern if widely used, otherwise fallback to text before first '{'
        # Or sometimes models just output text then JSON.
        # Let's try to capture everything before the first `{` as thought if no tags exist
        # But be careful not to capture empty strings if JSON starts immediately
        pass

    # 2. Extract JSON
    # Find the first curly brace
    start_idx = text.find('{')
    if start_idx != -1:
        # If we didn't find explicit think tags, treat everything before JSON as thought
        if not thought:
            thought = text[:start_idx].strip()
            # Clean up potential trailing tags/labels from the thought part if needed

        # Try to parse JSON from start_idx to the end, or find the matching closing brace
        # Simple stack-based brace matching
        brace_count = 0
        json_str = ""
        for char in text[start_idx:]:
            json_str += char
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    break

        try:
            json_data = json.loads(json_str)
            is_json = True
        except json.JSONDecodeError:
            # Fallback: maybe just return the raw string or fail
            pass
    else:
        # No JSON found, maybe the whole text is thought?
        if not thought:
            thought = text.strip()

    return {
        "thought": thought,
        "data": json_data if is_json else text, # Return parsed dict or original text if no JSON
        "is_json": is_json
    }
