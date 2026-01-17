import unittest
import io
import json
from unittest.mock import MagicMock, patch, AsyncMock
from medgemma_triage import utils
from medgemma_triage import tools

class TestUtils(unittest.IsolatedAsyncioTestCase):
    def test_encode_to_base64_string(self):
        f = io.BytesIO(b"hello world")
        b64 = utils.encode_to_base64(f)
        self.assertEqual(b64, "aGVsbG8gd29ybGQ=")

    @patch("medgemma_triage.utils.httpx.AsyncClient")
    async def test_call_fastmcp_tool_success(self, mock_client_cls):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Tool Result"}],
            "isError": False
        }
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        # When mocking AsyncClient as a context manager if needed, but here we pass client directly
        # The function signature is call_fastmcp_tool_async(name, args, client)

        result = await utils.call_fastmcp_tool_async("test_tool", {}, mock_client)
        self.assertEqual(result, "Tool Result")

    @patch("medgemma_triage.utils.httpx.AsyncClient")
    async def test_call_fastmcp_tool_error_flag(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Something broke"}],
            "isError": True
        }
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        result = await utils.call_fastmcp_tool_async("test_tool", {}, mock_client)
        self.assertIn("Connection Error (test_tool): FastMCP Tool Error: Something broke", result)

if __name__ == "__main__":
    unittest.main()
