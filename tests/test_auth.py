import unittest
from unittest.mock import patch, MagicMock
import hashlib
from medgemma_triage import auth

class TestAuth(unittest.TestCase):

    @patch('medgemma_triage.auth.get_redis_client')
    def test_verify_user_success(self, mock_get_redis_client):
        """Test successful user verification."""
        # Setup mock Redis client
        mock_redis = MagicMock()
        mock_get_redis_client.return_value = mock_redis

        # Setup stored password hash
        username = "testuser"
        password = "password123"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        mock_redis.hget.return_value = password_hash

        # Call the function and assert the result
        self.assertTrue(auth.verify_user(username, password))
        mock_redis.hget.assert_called_with(f"user:{username}", "password_hash")

    @patch('medgemma_triage.auth.get_redis_client')
    def test_verify_user_failure_wrong_password(self, mock_get_redis_client):
        """Test failed user verification due to wrong password."""
        mock_redis = MagicMock()
        mock_get_redis_client.return_value = mock_redis

        username = "testuser"
        stored_password = "password123"
        wrong_password = "wrongpassword"
        password_hash = hashlib.sha256(stored_password.encode()).hexdigest()
        mock_redis.hget.return_value = password_hash

        self.assertFalse(auth.verify_user(username, wrong_password))

    @patch('medgemma_triage.auth.get_redis_client')
    def test_verify_user_failure_no_user(self, mock_get_redis_client):
        """Test failed user verification due to non-existent user."""
        mock_redis = MagicMock()
        mock_get_redis_client.return_value = mock_redis
        mock_redis.hget.return_value = None

        self.assertFalse(auth.verify_user("nonexistentuser", "password"))

if __name__ == '__main__':
    unittest.main()
