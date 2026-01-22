import asyncio
import streamlit as st
from fastmcp import Client
from .utils import get_secret # Using relative import

async def call_backend_tool_async(tool_name, arguments={}):
    """
    Asynchronously calls a tool on the backend MCP server using SSE.
    """
    mcp_url = get_secret("MCP_SERVER_URL")
    if not mcp_url:
        st.error("MCP_SERVER_URL is not configured in st.secrets.")
        return None

    try:
        async with Client(mcp_url) as client:
            result = await client.call_tool(tool_name, arguments=arguments)
            if hasattr(result, 'content'):
                return "".join([c.text for c in result.content if c.type == 'text'])
            return str(result)
    except Exception as e:
        st.error(f"Error calling backend tool '{tool_name}': {e}")
        return None

def call_backend_tool(tool_name, arguments={}):
    """
    Synchronous wrapper for calling a backend tool.
    """
    return asyncio.run(call_backend_tool_async(tool_name, arguments))

async def list_backend_tools_async():
    """
    Asynchronously lists available tools from the MCP server.
    """
    mcp_url = get_secret("MCP_SERVER_URL")
    if not mcp_url:
        st.error("MCP_SERVER_URL is not configured in st.secrets.")
        return None

    async with Client(mcp_url) as client:
        return await client.list_tools()

def list_backend_tools():
    """
    Synchronous wrapper for listing available backend tools.
    """
    return asyncio.run(list_backend_tools_async())
