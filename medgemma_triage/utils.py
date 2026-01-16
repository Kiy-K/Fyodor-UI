import json
import re

# Pre-compile regex patterns for efficiency
THOUGHT_PATTERN = re.compile(
    r'(<unused94>thought|<think>)(.*?)(<unused95>|</think>)',
    re.DOTALL
)
JSON_PATTERN = re.compile(r'\{.*\}', re.DOTALL)


def parse_medgemma_response(raw_text: str) -> dict:
    """
    Robust parser for MedGemma responses.
    Supports both <think>...</think> and <unused94>thought...<unused95> formats.
    Returns a dict with thought, is_json flag, and content.
    """
    # 1. Extract Thought (support both <think> and <unused94>)
    thought_match = THOUGHT_PATTERN.search(raw_text)
    thought = thought_match.group(2).strip() if thought_match else ""
    
    # 2. Extract JSON (Robust fallback)
    # Remove thought block from text first
    clean_text = THOUGHT_PATTERN.sub('', raw_text).strip()
    
    json_data = None
    try:
        json_match = JSON_PATTERN.search(clean_text)
        if json_match:
            json_data = json.loads(json_match.group(0))
    except (json.JSONDecodeError, Exception):
        pass

    return {
        "thought": thought,
        "is_json": json_data is not None,
        "content": json_data if json_data else clean_text
    }
