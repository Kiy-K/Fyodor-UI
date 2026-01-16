import unittest
import sys
import os

# Add the directory to path
sys.path.append("medgemma_triage")
import utils

class TestMedGemmaUtils(unittest.TestCase):
    def test_parse_medgemma_response_simple(self):
        raw = "<unused94>thought\nThinking...\n<unused95>\nHello World"
        parsed = utils.parse_medgemma_response(raw)
        self.assertEqual(parsed['thought'], "Thinking...")
        self.assertEqual(parsed['markdown_report'], "Hello World")
        self.assertIsNone(parsed['json_data'])

    def test_parse_medgemma_response_with_json_block(self):
        raw = """<think>
        Analysis complete.
        </think>
        # Report
        Patient stable.

        ```json
        {"news2_score": 5, "triage_level": "Urgent"}
        ```
        """
        parsed = utils.parse_medgemma_response(raw)
        self.assertEqual(parsed['thought'], "Analysis complete.")
        self.assertEqual(parsed['json_data']['news2_score'], 5)
        self.assertNotIn("```json", parsed['markdown_report'])
        self.assertIn("# Report", parsed['markdown_report'])

if __name__ == '__main__':
    unittest.main()
