import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add medgemma_triage to path so we can import modules
sys.path.append(os.path.join(os.getcwd(), 'medgemma_triage'))

import utils
import tools

class TestUtils(unittest.TestCase):
    def test_extract_search_command(self):
        text = "Some thought process... [SEARCH: severe chest pain] ... more text"
        self.assertEqual(utils.extract_search_command(text), "severe chest pain")

        text2 = "No search here"
        self.assertIsNone(utils.extract_search_command(text2))

    def test_parse_medgemma_response_full(self):
        text = """<think>
This is a thought.
</think>
{
  "triage_level": "EMERGENCY",
  "reason": "Test"
}"""
        result = utils.parse_medgemma_response(text)
        self.assertEqual(result["thought"], "This is a thought.")
        self.assertTrue(result["is_json"])
        self.assertEqual(result["data"]["triage_level"], "EMERGENCY")

    def test_parse_medgemma_response_no_tags(self):
        text = """Thinking about stuff...
{
  "triage_level": "STABLE"
}"""
        result = utils.parse_medgemma_response(text)
        self.assertEqual(result["thought"], "Thinking about stuff...")
        self.assertTrue(result["is_json"])
        self.assertEqual(result["data"]["triage_level"], "STABLE")

class TestTools(unittest.TestCase):
    @patch('tools.Client')
    def test_list_tools(self, mock_client_cls):
        # Setup Mock
        mock_client_instance = MagicMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client_instance

        # Define async return value
        async def mock_list():
            return [{"name": "search_pubmed"}, {"name": "triage_patient"}]

        mock_client_instance.list_tools.side_effect = mock_list

        # Run
        tools_list = tools.list_tools()

        # Assert
        self.assertEqual(len(tools_list), 2)
        self.assertEqual(tools_list[0]["name"], "search_pubmed")

if __name__ == '__main__':
    unittest.main()
