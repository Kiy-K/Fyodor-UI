import asyncio
from fastmcp import Client

MCP_SERVER_URL = "https://med-mcp.fastmcp.app/mcp"

def run_sync(coroutine):
    """
    Helper to run async code synchronously, compatible with Streamlit.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We are in an existing loop (e.g. Streamlit's loop if it exists),
        # but we need to block for the result.
        # This is tricky in Streamlit. Usually asyncio.run works if called from a thread
        # that isn't the main loop, or we just create a new loop if none exists.
        # Streamlit execution model often allows creating a new loop if we are not deep in async context.
        # However, if 'get_running_loop' succeeds, we can't use 'asyncio.run'.
        # For simplicity in many Streamlit apps, creating a new event loop policy or using asyncio.run
        # on the top level logic works.
        # But if we are inside a callback...
        # Let's try to just return a Future? No, we need sync result.

        # Strategy: Use a separate thread to run the loop if one is already running?
        # Or just use asyncio.create_task if we were async. But we are sync.

        # Best practice for 'run_sync' in a potentially already-looped environment
        # without being async ourselves is complex.
        # However, Streamlit script runs in a thread. 'asyncio.get_running_loop()' usually raises RuntimeError
        # unless we are in an async def called by a runner.

        # If we encounter a running loop, we can't easily block on it from the same thread.
        # We will assume standard Streamlit usage where top-level script is not in a loop yet.
        future = asyncio.ensure_future(coroutine)
        return loop.run_until_complete(future)
    else:
        return asyncio.run(coroutine)

def query_jules_mcp(user_query: str, tool_name: str = "chat"):
    """
    Synchronous wrapper to query the FastMCP backend.
    """
    async def _query():
        async with Client(MCP_SERVER_URL) as client:
            # Assuming client.call_tool returns the result directly or a response object
            # Adjust param key "query" based on tool definition
            result = await client.call_tool(tool_name, {"query": user_query})
            return result

    return run_sync(_query())
