import json
import re
import base64

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
    # 1. Extract Thought (support both <think> and <unused94>)
    thought_match = THOUGHT_PATTERN.search(raw_text)
    thought = thought_match.group(2).strip() if thought_match else ""
    
    # 2. Extract JSON (Robust fallback)
    # Remove thought block from text first
    clean_text = THOUGHT_PATTERN.sub('', raw_text).strip()
    
    # 2. Extract JSON (if any)
    json_data = None
    try:
        json_match = JSON_PATTERN.search(clean_text)
        if json_match:
            json_data = json.loads(json_match.group(0))
    except (json.JSONDecodeError, Exception):
        pass

    return {
        "thought": thought,
        "json_data": json_data,
        "markdown_report": markdown_report
    }
