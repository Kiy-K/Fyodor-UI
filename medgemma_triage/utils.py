import os
import json
import httpx
import base64
import asyncio
import re
from typing import AsyncGenerator, Tuple, Dict, Any, List
from openai import AsyncOpenAI
import streamlit as st

# Import from the new tools module
from medgemma_triage.tools import TOOLS_SCHEMA, call_tool_async

# --- Configuration ---
def get_config(key, default=None):
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)

MEDGEMMA_API_URL = get_config("MEDGEMMA_API_URL", "http://localhost:30000/v1")
MEDGEMMA_API_KEY = get_config("MEDGEMMA_API_KEY", "EMPTY")

# --- Compiled Regex ---
THOUGHT_PATTERN = re.compile(r'<think>(.*?)</think>', re.DOTALL)
THOUGHT_REMOVE_PATTERN = re.compile(r'<think>.*?</think>', re.DOTALL)
JSON_PATTERN = re.compile(r'(\{.*\})', re.DOTALL)

# --- Helper Functions ---

def parse_medgemma_response(raw_text: str) -> Dict[str, Any]:
    """
    Parses the response from MedGemma which might include <think> tags.
    Extracts 'thought', 'markdown_report', and attempts to parse any JSON.
    """
    thought = ""
    # Extract thought block
    thought_match = THOUGHT_PATTERN.search(raw_text)
    if thought_match:
        thought = thought_match.group(1).strip()
        # Remove thought from the main text for the report
        clean_text = THOUGHT_REMOVE_PATTERN.sub('', raw_text).strip()
    else:
        clean_text = raw_text.strip()

    # Try to find JSON at the end or standalone
    json_data = {}
    # Simple heuristic to find a JSON object
    try:
        # Look for { ... } block
        json_match = JSON_PATTERN.search(clean_text)
        if json_match:
            potential_json = json_match.group(1)
            json_data = json.loads(potential_json)
    except:
        pass

    return {
        "thought": thought,
        "markdown_report": clean_text,
        "json_data": json_data
    }

def encode_to_base64(file_obj) -> str:
    """Encodes a file-like object to Base64 string."""
    if file_obj is None:
        return None
    try:
        # Reset pointer if possible
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)

        if hasattr(file_obj, 'read'):
            file_bytes = file_obj.read()
        else:
            file_bytes = file_obj

        return base64.b64encode(file_bytes).decode('utf-8')
    except Exception as e:
        return None

# --- The Agent Loop ---

async def run_agent_loop_async(
    user_input: str,
    context_files: Dict[str, Any],
    chat_history: List[Dict[str, str]]
) -> AsyncGenerator[Tuple[str, str], None]:
    """
    Manages the conversation loop with SGLang and FastMCP.
    Yields tuples of (status_type, content) to update the UI.
    """

    # 1. Initialize Async OpenAI Client for SGLang
    client_openai = AsyncOpenAI(
        base_url=MEDGEMMA_API_URL,
        api_key=MEDGEMMA_API_KEY
    )

    # 2. Construct Messages
    # System Prompt with Context Awareness
    system_content = "You are MedGemma, an expert clinical triage consultant."

    has_image = context_files.get("image") is not None
    has_audio = context_files.get("audio") is not None

    if has_image or has_audio:
        system_content += "\n\nCONTEXT LOADED:"
        if has_image:
            system_content += "\n- High-resolution X-Ray image is available. Use `analyze_xray_multiscale` or `extract_xray_metadata` (no arguments needed)."
        if has_audio:
            system_content += "\n- Clinical voice note is available. Use `transcribe_medical_audio` (no arguments needed)."
    
    messages = [{"role": "system", "content": system_content}]
    
    # Append History
    for msg in chat_history:
        messages.append(msg)

    # Append Current User Input
    messages.append({"role": "user", "content": user_input})

    # Yield initial status
    yield ("status", "Consulting MedGemma...")

    # Initialize shared HTTP client for tool calls
    async with httpx.AsyncClient(timeout=60.0) as http_client:

        # 3. The Tool Loop
        while True:
            try:
                # Call Model
                completion = await client_openai.chat.completions.create(
                    model="medgemma", # Model name usually ignored by SGLang if only one is served, but good practice
                    messages=messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto"
                )

                message = completion.choices[0].message

                # Check if the model wants to call a tool
                if message.tool_calls:
                    # Add the assistant's "thought" (tool call request) to history
                    messages.append(message)

                    for tool_call in message.tool_calls:
                        fn_name = tool_call.function.name
                        args_str = tool_call.function.arguments
                        args = json.loads(args_str) if args_str else {}

                        yield ("tool", f"Running Tool: {fn_name}...")

                        # --- CONTEXT INJECTION ---
                        # The model sends empty args, we inject the heavy Base64 data here.
                        if fn_name == "analyze_xray_multiscale" or fn_name == "extract_xray_metadata":
                            if has_image:
                                b64_img = encode_to_base64(context_files["image"])
                                args["image_base64"] = b64_img
                            else:
                                # If model hallucinates availability or we failed to load
                                pass

                        elif fn_name == "transcribe_medical_audio":
                            if has_audio:
                                b64_audio = encode_to_base64(context_files["audio"])
                                args["audio_base64"] = b64_audio
                            else:
                                pass

                        # Execute Tool
                        # Changed: Using call_tool_async imported from tools.py
                        result = await call_tool_async(fn_name, args, client=http_client)

                        # Add result to history
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })

                        yield ("tool_result", f"Finished {fn_name}")

                else:
                    # No tool calls, this is the final answer
                    final_content = message.content
                    yield ("content", final_content)
                    break

            except Exception as e:
                yield ("error", f"Agent Loop Error: {str(e)}")
                break
