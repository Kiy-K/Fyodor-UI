import re
import json
import os
import streamlit as st

def get_secret(key, default=None):
    """
    Retrieves a secret from Streamlit secrets (priority) or environment variables.

    Args:
        key (str): The name of the secret/environment variable.
        default (any): The default value if not found.

    Returns:
        str or None: The secret value.
    """
    try:
        # st.secrets acts like a dictionary
        if key in st.secrets:
            return st.secrets[key]
    except (FileNotFoundError, AttributeError):
        # st.secrets might fail if not running in Streamlit or no secrets.toml
        pass

    return os.getenv(key, default)

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

def parse_medgemma_response(text, source="expert"):
    """
    Parses the model response to extract:
    1. Thought process (inside <think>...</think> or <unused94>thought...)
    2. JSON data (intelligent extraction of first valid JSON object)
    3. Content (remaining human-readable text)

    Args:
        text (str): The raw model response.
        source (str): "expert" or "fast".
                      - "expert" implies Modal/Gemma (strict tags expected).
                      - "fast" implies Groq/Llama (might be chatty).

    Returns:
        dict: {"thought": str, "content": str, "is_json": bool, "data": dict}
    """
    if not text:
        return {"thought": "", "content": "", "is_json": False, "data": {}}

    thought = ""
    json_data = {}
    is_json = False

    # Work on a working copy of text to strip out parts we extract
    remaining_text = text

    # --- 1. Extract Thought ---
    # Strategy: Find and extract, then remove from remaining_text

    # Pattern A: <think>...</think>
    think_match = re.search(r"<think>(.*?)</think>", remaining_text, re.DOTALL)
    if think_match:
        thought = think_match.group(1).strip()
        # Remove the whole tag block from remaining text
        remaining_text = remaining_text.replace(think_match.group(0), "")

    # Pattern B: <unused94>thought... (Gemma specific)
    # This usually appears at the start. It might not have a closing tag,
    # or it might just be the thought section.
    # We'll treat it as: <unused94>thought [content]
    # Sometimes it's just a marker.
    elif "<unused94>thought" in remaining_text:
        # Regex to capture content after marker
        # We assume it goes until the next specific marker or just treat it carefully.
        # Often it replaces <think>. Let's try to capture it.
        # If we see this, we might assume the thought is what follows until we hit JSON or end?
        # A robust way is to just strip the marker and treat it as thought if no JSON,
        # or rely on the fact that if we didn't find <think>, we look for JSON next.
        pass
        # Actually, user said: "<unused94>thought appears as a literal string... Treat it exactly like that."
        # If it acts like an open tag without close, we might need to assume it ends at JSON start.

    # --- 2. Extract JSON ---
    # Find first '{' and last '}'
    start_idx = remaining_text.find('{')
    last_idx = remaining_text.rfind('}')

    extracted_json_str = ""

    if start_idx != -1 and last_idx != -1 and last_idx > start_idx:
        potential_json = remaining_text[start_idx : last_idx + 1]
        try:
            json_data = json.loads(potential_json)
            is_json = True
            extracted_json_str = potential_json
            # Remove the JSON block from remaining text
            # We must be careful if the same JSON string appears multiple times,
            # but usually it's unique enough.
            remaining_text = remaining_text.replace(potential_json, "", 1)
        except json.JSONDecodeError:
            # Maybe the range includes extra garbage?
            # Fallback: Try a stricter brace balancer if simple slice failed?
            # Or just accept it failed.
            pass

    # --- 3. Fallback Thought Extraction (if no tags found) ---
    # If source is expert and we didn't find <think>, but found JSON,
    # maybe text before JSON is thought?
    # BUT, the requirement said "Use robust Regex that handles... <unused94>thought".
    if not thought and "<unused94>thought" in text:
        # It's likely the text starting with this marker is the thought.
        # If JSON was extracted, the thought is everything from marker up to JSON.
        # If JSON was NOT extracted, everything is thought?
        # Let's try to parse it from the original text context.

        # Re-evaluating from original text to find relative positions
        marker_idx = text.find("<unused94>thought")
        if marker_idx != -1:
            if is_json:
                # Thought is between marker and JSON start
                # We need to find where JSON started in original text
                json_start_in_orig = text.find(extracted_json_str)
                if json_start_in_orig > marker_idx:
                    raw_thought = text[marker_idx + len("<unused94>thought"):json_start_in_orig]
                    thought = raw_thought.strip()
            else:
                # No JSON, so everything after marker is thought
                thought = text[marker_idx + len("<unused94>thought"):].strip()

            # Now we need to make sure remaining_text (content) doesn't have the thought or the marker
            # We already removed JSON from remaining_text (if found).
            # We need to remove the thought part from remaining_text too.
            remaining_text = remaining_text.replace("<unused94>thought", "")
            if thought:
                remaining_text = remaining_text.replace(thought, "")

    # --- 4. Define Content ---
    content = remaining_text.strip()

    # Edge Case: If output is ONLY JSON, content should be empty.
    # (Handled by stripping remaining_text)

    # Edge Case: If no thought tags and not <unused94>, and source="expert",
    # usually expert follows protocol. If source="fast", it might just chat.
    # We accept whatever remains as content.

    return {
        "thought": thought,
        "content": content,
        "is_json": is_json,
        "data": json_data
    }
