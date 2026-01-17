import os
import json
import httpx
import asyncio
import base64
import re
import streamlit as st

# --- Configuration ---
# Helper to get config from st.secrets or os.getenv
def get_config(key, default=None):
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)

MCP_SERVER_URL = get_config("MCP_SERVER_URL", "http://localhost:8000")

# Ensure URL ends correctly for the specific endpoint structure requested
# The user specified: POST /call_tool (appended to Base URL)
# If MCP_SERVER_URL includes /call_tool, use it, otherwise append.
if not MCP_SERVER_URL.endswith("/call_tool"):
    MCP_TOOL_ENDPOINT = f"{MCP_SERVER_URL.rstrip('/')}/call_tool"
else:
    MCP_TOOL_ENDPOINT = MCP_SERVER_URL

# --- API Wrappers ---

async def call_mcp_tool_async(tool_name: str, args: dict) -> str:
    """
    Async function to call the FastMCP HTTP endpoint.
    """
    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        payload = {
            "name": tool_name,
            "arguments": args
        }
        try:
            response = await client.post(MCP_TOOL_ENDPOINT, json=payload)
            response.raise_for_status()

            # FastMCP usually returns the result content.
            # If the tool returns a string, it might be in response.text or response.json() depending on implementation.
            # Assuming standard JSON response where the result might be wrapped or just the content.
            # However, the user said "FastMCP Cloud".
            # Let's return the text body for maximum flexibility, or parse if it's JSON.

            # If the response is JSON, let's try to see if it has a 'content' field or similar.
            # But specific instructions said: Payload Structure for request.
            # It didn't specify response structure. I'll assume the body IS the result or contains it.
            # Let's try to return the text.
            return response.text

        except httpx.HTTPStatusError as e:
            return f"Error calling {tool_name}: {e.response.text}"
        except Exception as e:
            return f"Connection Error ({tool_name}): {str(e)}"

def call_mcp_tool(tool_name: str, args: dict) -> str:
    """
    Synchronous wrapper for calling a single tool.
    """
    return asyncio.run(call_mcp_tool_async(tool_name, args))

def run_chat(messages: list) -> str:
    """
    Wrapper for SGLang Chat Proxy tool.
    Expects a list of dicts: [{"role": "user", "content": "..."}]
    """
    return call_mcp_tool("chat_with_consultant", {"messages": messages})

async def gather_analysis_inputs(audio_file, image_file):
    """
    Orchestrates the parallel execution of:
    1. Audio Transcription (if audio_file provided)
    2. Image Analysis (if image_file provided)
    3. Image Metadata (if image_file provided)
    """
    tasks = []
    task_names = []

    # 1. Audio Task
    if audio_file:
        b64_audio = encode_to_base64(audio_file)
        tasks.append(call_mcp_tool_async("transcribe_medical_audio", {"audio_base64": b64_audio}))
        task_names.append("audio")
    else:
        # Placeholder if no audio
        tasks.append(asyncio.sleep(0, result="No audio provided."))
        task_names.append("audio")

    # 2 & 3. Image Tasks
    if image_file:
        b64_image = encode_to_base64(image_file)
        # Task: Analysis
        tasks.append(call_mcp_tool_async("analyze_xray_multiscale", {"image_base64": b64_image}))
        task_names.append("image_analysis")
        # Task: Metadata
        tasks.append(call_mcp_tool_async("extract_xray_metadata", {"image_base64": b64_image}))
        task_names.append("image_metadata")
    else:
        tasks.append(asyncio.sleep(0, result="No image provided."))
        task_names.append("image_analysis")
        tasks.append(asyncio.sleep(0, result="No image metadata."))
        task_names.append("image_metadata")

    # Run in parallel
    results = await asyncio.gather(*tasks)

    # Return a dictionary for easy access
    return dict(zip(task_names, results))


# --- Data Parsing & Formatting ---

# Pre-compile regex patterns for efficiency
THOUGHT_PATTERN = re.compile(
    r'(<unused94>thought|<think>)(.*?)(<unused95>|</think>)',
    re.DOTALL
)
JSON_PATTERN = re.compile(r'\{.*\}', re.DOTALL)

def parse_medgemma_response(raw_text: str) -> dict:
    """
    Robust parser for MedGemma responses.
    Extracts 'thought' and 'markdown_report'.
    """
    if not raw_text:
        return {"thought": "", "json_data": None, "markdown_report": ""}

    # Handle potential JSON wrapping from FastMCP/httpx response
    # Sometimes the API returns "result" wrapped in quotes or JSON.
    # If raw_text looks like a JSON string containing the actual text, we might need to unwrap.
    # But let's assume raw_text is the content for now.

    # 1. Extract Thought
    thought_match = THOUGHT_PATTERN.search(raw_text)
    thought = thought_match.group(2).strip() if thought_match else ""
    
    # Remove thought block from text to get the report content
    clean_text = THOUGHT_PATTERN.sub('', raw_text).strip()
    
    # 2. Extract JSON (if any) - optional logic
    json_data = None
    try:
        json_match = JSON_PATTERN.search(clean_text)
        if json_match:
            json_str = json_match.group(0)
            json_data = json.loads(json_str)
    except Exception:
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
        if hasattr(file_obj, 'read'):
            file_bytes = file_obj.read()
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
        else:
            file_bytes = file_obj

        return base64.b64encode(file_bytes).decode('utf-8')
    except Exception as e:
        return None
