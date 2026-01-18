import asyncio
import os
import base64
import io
import httpx
import streamlit as st
from fastmcp import Client
from dotenv import load_dotenv
from groq import Groq
from utils import get_secret

load_dotenv()

# Global variable for the embedding model (Lazy Loading) - Cached resource
@st.cache_resource
def get_embedding_model():
    """
    Singleton to load the embedding model only once.
    """
    try:
        from sentence_transformers import SentenceTransformer
        # Load the model (runs efficiently on CPU)
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model
    except ImportError:
        raise ImportError("sentence-transformers is not installed. Please install it.")
    except Exception as e:
        raise RuntimeError(f"Failed to load embedding model: {e}")

async def _call_tool_async(tool_name, args=None):
    """
    Async implementation to call an MCP tool using SSE.
    """
    if args is None:
        args = {}

    mcp_url = get_secret("MCP_SERVER_URL", "https://med-mcp.fastmcp.app/sse")

    # Create the client.
    # Note: fastmcp.Client uses 'url' for SSE.
    async with Client(mcp_url) as client:
        result = await client.call_tool(tool_name, arguments=args)
        return result

def call_mcp_tool(tool_name, args=None):
    """
    Synchronous wrapper for calling MCP tools.
    """
    return asyncio.run(_call_tool_async(tool_name, args))

async def _list_tools_async():
    mcp_url = get_secret("MCP_SERVER_URL", "https://med-mcp.fastmcp.app/sse")
    async with Client(mcp_url) as client:
        tools = await client.list_tools()
        return tools

def list_tools():
    """
    Lists available tools from the MCP server.
    """
    try:
        return asyncio.run(_list_tools_async())
    except Exception as e:
        return [f"Error listing tools: {str(e)}"]

def search_pubmed(query):
    """
    Calls the 'search_pubmed' tool on the MCP server.
    """
    try:
        # Assuming the remote tool is named 'search_pubmed' and takes 'query'
        result = call_mcp_tool("search_pubmed", {"query": query})

        # fastmcp result might be an object with content, or just the content depending on version.
        # Usually it returns a CallToolResult which has content list.
        # We need to serialize it to string for the LLM.
        if hasattr(result, 'content'):
            return "\n".join([c.text for c in result.content if c.type == 'text'])
        return str(result)
    except Exception as e:
        return f"Error searching PubMed: {str(e)}"

def triage_patient(data):
    """
    Calls the 'triage_patient' tool on the MCP server.
    """
    try:
        # data is expected to be a dict corresponding to the tool's schema
        result = call_mcp_tool("triage_patient", data)
        if hasattr(result, 'content'):
            return "\n".join([c.text for c in result.content if c.type == 'text'])
        return str(result)
    except Exception as e:
        return f"Error triaging patient: {str(e)}"

def transcribe_legacy(file_bytes):
    """
    Encodes audio bytes to Base64 and calls the 'transcribe_medical_audio' tool on the MCP server.
    """
    try:
        # Encode bytes to base64 string
        base64_audio = base64.b64encode(file_bytes).decode('utf-8')

        # Call the MCP tool
        result = call_mcp_tool("transcribe_medical_audio", {"audio_data": base64_audio})

        if hasattr(result, 'content'):
            return "\n".join([c.text for c in result.content if c.type == 'text'])
        return str(result)
    except Exception as e:
        return f"Error transcribing audio (Legacy): {str(e)}"

def transcribe_audio(file_bytes):
    """
    Transcribes audio using Groq Whisper-Large-V3.
    """
    api_key = get_secret("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not configured."

    try:
        client = Groq(api_key=api_key)

        # Create a file-like object from bytes
        audio_file = io.BytesIO(file_bytes)
        audio_file.name = "recording.wav" # Groq requires a filename

        # Call Groq Whisper API
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            prompt="Medical dictation. Patient history, cardiology, hypertension, medication, symptoms.", # Context priming
            response_format="json",
            temperature=0.0 # Strict accuracy
            # language=None # Auto-detect
        )
        return transcription.text
    except Exception as e:
        return f"Transcription Error (Groq): {str(e)}"

def generate_embedding(text):
    """
    Generates an embedding for the given text using sentence-transformers (all-MiniLM-L6-v2).
    """
    try:
        model = get_embedding_model()
        # encode returns a numpy array or list depending on configuration, we want list of floats
        embedding = model.encode(text)
        return embedding.tolist()
    except Exception as e:
        # In case of error, returning specific error message or empty list might be safer depending on consumer.
        # But for now, returning formatted error string to be visible in logs/UI if printed.
        # However, caller expects list. Let's raise or return empty?
        # The prompt didn't specify error handling, but usually we don't want to crash.
        # Let's print error and return empty list or raise.
        # Given this is a backend tool function, raising or returning error string is common,
        # but type hint was list[float].
        # Let's return None or raise so caller knows it failed.
        # For this implementation, I will return an empty list and log error string to console/return str?
        # To match other tools, I'll return the error string if I can, but the type signature expectation is list[float].
        # I'll convert error to string if called directly, but if used programmatically it might break.
        # I will let the exception propagate or return a descriptive error in a way handled by caller?
        # Actually, let's just return the error string as other tools do, assuming caller handles type mismatch or displays it.
        return f"Embedding Error: {str(e)}"

def call_fast_triage(messages):
    """
    Calls the Groq API (Fast Path) using lmeta-llama/llama-4-maverick-17b-128e-instruct.
    """
    api_key = get_secret("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not configured."

    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=messages,
            temperature=0.3,
            max_completion_tokens=4096,
            top_p=1,
            stop=None,
            stream=False,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Fast Triage Error (Groq): {str(e)}"
