import os
import json
import httpx
import streamlit as st
from typing import List, Dict, Any

# --- Configuration ---
def get_config(key, default=None):
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)

MCP_SERVER_URL = get_config("MCP_SERVER_URL", "http://localhost:8000")

# Ensure URL ends correctly for the specific endpoint
if not MCP_SERVER_URL.endswith("/call_tool"):
    MCP_TOOL_ENDPOINT = f"{MCP_SERVER_URL.rstrip('/')}/call_tool"
else:
    MCP_TOOL_ENDPOINT = MCP_SERVER_URL

# --- Shared Client ---
# Initialize a shared client for performance
# We use a timeout of 60s for potentially long running tools
_HTTP_CLIENT = httpx.Client(timeout=60.0)

# --- Tool Definitions ---
# Note: Media tools have EMPTY parameters in the schema exposed to the LLM.
# The actual heavy data is injected by the frontend.
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "transcribe_medical_audio",
            "description": "Transcribes clinical voice notes from the attached audio context.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_xray_multiscale",
            "description": "Analyzes the attached X-Ray image for clinical findings.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_xray_metadata",
            "description": "Extracts patient metadata (Name, DOB, ID) via OCR from the attached X-Ray.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "triage_patient",
            "description": "Calculates the NEWS2 score and clinical risk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hr": {"type": "integer", "description": "Heart Rate"},
                    "sbp": {"type": "integer", "description": "Systolic Blood Pressure"},
                    "rr": {"type": "integer", "description": "Respiratory Rate"},
                    "temp": {"type": "number", "description": "Temperature in Celsius"},
                    "spo2": {"type": "integer", "description": "Oxygen Saturation (%)"},
                    "consciousness": {"type": "string", "enum": ["Alert", "Voice", "Pain", "Unresponsive"]},
                    "oxygen": {"type": "boolean", "description": "Is patient on supplemental oxygen?"}
                },
                "required": ["hr", "sbp", "rr", "temp", "spo2", "consciousness", "oxygen"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sequential_thinking",
            "description": "A tool for structured clinical reasoning and step-by-step analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {"type": "string", "description": "The current step of reasoning."},
                    "needs_more_time": {"type": "boolean", "description": "If true, the model needs to think more."}
                },
                "required": ["thought", "needs_more_time"]
            }
        }
    }
]

def call_fastmcp_tool(tool_name: str, args: dict) -> str:
    """
    Synchronously calls the FastMCP Cloud endpoint via HTTP POST.
    Uses a shared httpx.Client for performance.
    """
    payload = {
        "name": tool_name,
        "arguments": args
    }

    try:
        # Use the shared client
        response = _HTTP_CLIENT.post(MCP_TOOL_ENDPOINT, json=payload)
        response.raise_for_status()

        # Parse MCP JSON-RPC Response
        resp_data = response.json()

        if resp_data.get("isError"):
            content = resp_data.get("content", [])
            error_msg = "Unknown Error"
            if content and isinstance(content, list) and len(content) > 0:
                    error_msg = content[0].get("text", str(content))
            raise Exception(f"FastMCP Tool Error: {error_msg}")

        content = resp_data.get("content", [])
        if not content or not isinstance(content, list):
            return ""

        # Return text from the first content block
        first_block = content[0]
        if first_block.get("type") == "text":
            return first_block.get("text", "")
        return str(first_block)

    except httpx.HTTPStatusError as e:
        return f"Error calling {tool_name}: {e.response.text}"
    except Exception as e:
        return f"Connection Error ({tool_name}): {str(e)}"

def get_available_tools():
    """
    Helper to list tools for debugging.
    This was requested in the task description.
    Since we don't have the 'mcp' library Client, we use a placeholder
    or we could implement it if the FastMCP endpoint supports 'list_tools'.
    For now, we return the local schema as a representation.
    """
    # If the endpoint supports a list_tools capability via POST or GET, we could use _HTTP_CLIENT here.
    # But based on the provided code snippet which used 'await client.list_tools()',
    # and since we are strictly in 'httpx' land, we will just return the local definitions or a message.

    # Implementing a best-effort list_tools using the JSON-RPC if possible,
    # or just returning the static schema for now as we don't know the list method name for the endpoint.
    return TOOLS_SCHEMA
