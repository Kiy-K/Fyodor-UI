import asyncio
import os
from fastmcp import Client
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://med-mcp.fastmcp.app/sse")

async def _call_tool_async(tool_name, args=None):
    """
    Async implementation to call an MCP tool using SSE.
    """
    if args is None:
        args = {}

    # Create the client.
    # Note: fastmcp.Client uses 'url' for SSE.
    async with Client(url=MCP_SERVER_URL) as client:
        result = await client.call_tool(tool_name, arguments=args)
        return result

def call_mcp_tool(tool_name, args=None):
    """
    Synchronous wrapper for calling MCP tools.
    """
    return asyncio.run(_call_tool_async(tool_name, args))

async def _list_tools_async():
    async with Client(url=MCP_SERVER_URL) as client:
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
