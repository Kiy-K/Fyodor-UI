import unittest
import io
import json
from unittest.mock import MagicMock, patch
from medgemma_triage import utils
from medgemma_triage import tools

class TestUtils(unittest.TestCase):
    def test_encode_to_base64_string(self):
        f = io.BytesIO(b"hello world")
        b64 = utils.encode_to_base64(f)
        self.assertEqual(b64, "aGVsbG8gd29ybGQ=")

    # Tests for tools.py (moved from utils)
    # Note: We now patch the shared client instance or the method call,
    # since we are no longer creating a new Client() inside the function.
    # The new implementation uses tools._HTTP_CLIENT

    @patch("medgemma_triage.tools._HTTP_CLIENT.post")
    def test_call_fastmcp_tool_success(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Tool Result"}],
            "isError": False
        }
        mock_response.raise_for_status.return_value = None

        mock_post.return_value = mock_response

        result = tools.call_fastmcp_tool("test_tool", {})
        self.assertEqual(result, "Tool Result")

    @patch("medgemma_triage.tools._HTTP_CLIENT.post")
    def test_call_fastmcp_tool_error_flag(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Something broke"}],
            "isError": True
        }
        mock_response.raise_for_status.return_value = None # ensure no http error

        mock_post.return_value = mock_response

        result = tools.call_fastmcp_tool("test_tool", {})
        self.assertIn("Connection Error (test_tool): FastMCP Tool Error: Something broke", result)

if __name__ == "__main__":
    unittest.main()
