import time
import asyncio
import httpx
import unittest
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Add repo root to path
sys.path.append(os.getcwd())

# Handle import differences for script execution
try:
    from medgemma_triage import tools, utils
except ImportError:
    # If running directly from tests folder without package context
    sys.path.append(os.path.join(os.getcwd(), 'medgemma_triage'))
    import tools
    import utils

# Mock Response Data
MOCK_RESPONSE_JSON = {
    "isError": False,
    "content": [{"type": "text", "text": "Tool Result Content"}]
}

def benchmark_sync_shared_client(n=1000):
    # Mock the internal _HTTP_CLIENT post method
    original_post = tools._HTTP_CLIENT.post
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = MOCK_RESPONSE_JSON
    tools._HTTP_CLIENT.post = mock_post

    start = time.perf_counter()
    for _ in range(n):
        tools.call_fastmcp_tool("test_tool", {})
    end = time.perf_counter()

    # Restore
    tools._HTTP_CLIENT.post = original_post
    return end - start

def benchmark_sync_fresh_client(n=1000):
    # Simulate function that creates a new client every time
    start = time.perf_counter()
    for _ in range(n):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=MOCK_RESPONSE_JSON))
        with httpx.Client(transport=transport) as c:
            c.post("http://localhost:8000/call_tool", json={})
    end = time.perf_counter()
    return end - start

async def benchmark_async_shared_client(n=1000):
    # Mock Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=MOCK_RESPONSE_JSON))
    async with httpx.AsyncClient(transport=transport) as client:
        start = time.perf_counter()
        for _ in range(n):
            # We use tools.call_tool_async (which accepts a client)
            await tools.call_tool_async("test_tool", {}, client)
        end = time.perf_counter()
    return end - start

async def benchmark_async_fresh_client(n=1000):
    start = time.perf_counter()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=MOCK_RESPONSE_JSON))
    for _ in range(n):
        async with httpx.AsyncClient(transport=transport) as client:
            await tools.call_tool_async("test_tool", {}, client)
    end = time.perf_counter()
    return end - start

def run_benchmarks():
    N = 500
    print(f"Running Benchmarks with N={N}...")

    # 1. Sync Shared
    t_sync_shared = benchmark_sync_shared_client(N)
    print(f"Sync (Shared Client): {t_sync_shared:.4f}s")

    # 2. Sync Fresh
    t_sync_fresh = benchmark_sync_fresh_client(N)
    print(f"Sync (Fresh Client):  {t_sync_fresh:.4f}s")

    print(f"Speedup Sync: {t_sync_fresh / t_sync_shared:.2f}x")

    # 3. Async Shared
    t_async_shared = asyncio.run(benchmark_async_shared_client(N))
    print(f"Async (Shared Client): {t_async_shared:.4f}s")

    # 4. Async Fresh
    t_async_fresh = asyncio.run(benchmark_async_fresh_client(N))
    print(f"Async (Fresh Client):  {t_async_fresh:.4f}s")

    print(f"Speedup Async: {t_async_fresh / t_async_shared:.2f}x")

if __name__ == "__main__":
    run_benchmarks()
