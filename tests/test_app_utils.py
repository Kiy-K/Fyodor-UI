import unittest
import io
import json
from medgemma_triage import utils

class TestUtils(unittest.TestCase):
    def test_parse_medgemma_response_full(self):
        raw = """<think>Thinking about the patient...</think>
        Here is the report.
        { "score": 5 }
        """
        parsed = utils.parse_medgemma_response(raw)
        self.assertEqual(parsed['thought'], "Thinking about the patient...")
        self.assertIn("Here is the report.", parsed['markdown_report'])
        self.assertEqual(parsed['json_data'], {"score": 5})

    def test_parse_medgemma_response_no_thought(self):
        raw = "Just a report."
        parsed = utils.parse_medgemma_response(raw)
        self.assertEqual(parsed['thought'], "")
        self.assertEqual(parsed['markdown_report'], "Just a report.")

    def test_encode_to_base64_string(self):
        # BytesIO acts like a file
        f = io.BytesIO(b"hello world")
        b64 = utils.encode_to_base64(f)
        # "hello world" in base64 is "aGVsbG8gd29ybGQ="
        self.assertEqual(b64, "aGVsbG8gd29ybGQ=")

if __name__ == '__main__':
    unittest.main()
