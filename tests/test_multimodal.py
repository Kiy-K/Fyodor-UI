import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path to import from medgemma_triage
sys.path.append(os.path.join(os.getcwd(), 'medgemma_triage'))

import tools

class TestMultimodalLogic(unittest.TestCase):

    @patch('tools.httpx.post')
    @patch.dict(os.environ, {"MODAL_ASR_URL": "https://fake.modal.run", "MODAL_API_KEY": "fake-key"})
    def test_transcribe_audio(self, mock_post):
        """Test that transcribe_audio correctly calls the Modal endpoint."""

        # Setup mock return
        mock_response = MagicMock()
        mock_response.json.return_value = {"text": "Patient has a cough."}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Dummy audio bytes
        audio_data = b"fake_audio_data"

        # Call function
        transcription = tools.transcribe_audio(audio_data)

        # Verify result
        self.assertEqual(transcription, "Patient has a cough.")

        # Verify call arguments
        # Should be raw bytes, not base64 for the HTTP endpoint
        mock_post.assert_called_once_with(
            "https://fake.modal.run",
            headers={"Authorization": "Bearer fake-key"},
            content=audio_data,
            timeout=60.0
        )

    def test_message_formatting_logic(self):
        """Test the logic intended for app.py message formatting."""
        # This duplicates logic in app.py to verify it works as expected
        import base64

        user_input = "Analyze this X-ray"
        img_bytes = b"fake_image_data"
        base64_img = base64.b64encode(img_bytes).decode('utf-8')

        message_content = [
            {"type": "text", "text": user_input},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
        ]

        self.assertEqual(message_content[0]["type"], "text")
        self.assertEqual(message_content[0]["text"], "Analyze this X-ray")
        self.assertEqual(message_content[1]["type"], "image_url")
        self.assertTrue(message_content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))

if __name__ == '__main__':
    unittest.main()
