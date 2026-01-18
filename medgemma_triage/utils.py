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

def strip_think_tags(text):
    """
    Removes <think>...</think> blocks from the text to show only the final assessment.
    Also handles <unused94>thought markers.
    """
    if not text:
        return ""

    cleaned_text = text

    # Remove <think>...</think> blocks
    cleaned_text = re.sub(r"<think>.*?</think>", "", cleaned_text, flags=re.DOTALL)

    # Remove <unused94>thought markers and potential content following it if it looks like a block
    # Given the user instruction "Strip out... <unused94>thought appears as a literal string",
    # we'll remove the marker. If it denotes a block without closing, it's harder,
    # but often it's just a prefix for the thought chain.
    # We will try to remove it and if there's a clear separation (like a JSON block), assume
    # text before JSON was thought.
    # However, for simple display purposes, just removing the marker is a safe first step,
    # but the goal is to hide the *internal reasoning*.
    # If the model outputs: "<unused94>thought I should checking X... \n Here is the diagnosis."
    # We want "Here is the diagnosis."

    # Let's reuse parse_medgemma_response logic which is more robust, or just implement a simple stripper
    # if we only want the final content.
    # Actually, parse_medgemma_response returns 'content' which already strips thought.
    # So this function might just wrap that or implement the regex logic specifically.

    # Let's keep it simple and strictly strip the tags as requested.
    # If <unused94>thought is used, we assume it starts a block.
    # If we find <unused94>thought, we might want to remove everything until the next newline
    # or until the end if it's all thought?
    # Without a closing tag for unused94, it's risky to strip too much.
    # But often it's followed by a newline.

    cleaned_text = cleaned_text.replace("<unused94>thought", "")

    return cleaned_text.strip()

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
    elif "<unused94>thought" in remaining_text:
        # If we see this, we assume it marks thought.
        # We strip the marker.
        # Logic is complex without end tag.
        # For now, just mark it exists.
        pass

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
            remaining_text = remaining_text.replace(potential_json, "", 1)
        except json.JSONDecodeError:
            pass

    # --- 3. Fallback Thought Extraction ---
    if not thought:
        if "<unused94>thought" in text:
            marker_idx = text.find("<unused94>thought")
            if marker_idx != -1:
                if is_json:
                    # Thought is between marker and JSON start
                    json_start_in_orig = text.find(extracted_json_str)
                    if json_start_in_orig > marker_idx:
                        raw_thought = text[marker_idx + len("<unused94>thought"):json_start_in_orig]
                        thought = raw_thought.strip()
                else:
                    # No JSON, so everything after marker is likely thought?
                    thought = text[marker_idx + len("<unused94>thought"):].strip()

                remaining_text = remaining_text.replace("<unused94>thought", "")
                if thought:
                    remaining_text = remaining_text.replace(thought, "")
        elif is_json:
            # Fallback: If no tags but we have JSON, treat text before JSON as thought
            json_start_in_orig = text.find(extracted_json_str)
            if json_start_in_orig > 0:
                potential_thought = text[:json_start_in_orig].strip()
                if potential_thought:
                    thought = potential_thought
                    remaining_text = remaining_text.replace(potential_thought, "", 1)

    # --- 4. Define Content ---
    content = remaining_text.strip()

    return {
        "thought": thought,
        "content": content,
        "is_json": is_json,
        "data": json_data
    }
