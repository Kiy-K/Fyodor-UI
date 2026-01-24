import streamlit as st
from upstash_redis import Redis
import hashlib

# --- Mock Redis for local development/testing ---
class MockRedis:
    """A mock Redis client that simulates Upstash Redis for local testing."""
    def __init__(self):
        self._data = {}
        print("Initialized MockRedis.")

    def exists(self, key):
        print(f"MOCK: Checking existence of '{key}'")
        return key in self._data

    def hgetall(self, key):
        print(f"MOCK: Getting all from '{key}'")
        return self._data.get(key, {})

    def hset(self, key, field, value):
        print(f"MOCK: Setting '{field}' for '{key}'")
        if key not in self._data:
            self._data[key] = {}
        self._data[key][field] = value

# --- Redis Client Initialization ---
def get_redis_client():
    """
    Initializes and returns a connection to Upstash Redis if secrets are available,
    otherwise returns a mock client for local testing.
    """
    try:
        # This will raise an exception if secrets are not configured
        if st.secrets.get("UPSTASH_REDIS_REST_URL"):
            return Redis(
                url=st.secrets["UPSTASH_REDIS_REST_URL"],
                token=st.secrets["UPSTASH_REDIS_REST_TOKEN"],
            )
    except st.errors.StreamlitAPIException as e:
        # This catches the specific error when secrets aren't found
        pass # Fall through to use mock client
    except Exception as e:
        # Catch other potential connection errors
        st.error(f"An unexpected error occurred: {e}")
        pass # Fall through to use mock client

    # Use mock client if secrets aren't found or are invalid
    if "mock_redis" not in st.session_state:
        st.session_state.mock_redis = MockRedis()
    return st.session_state.mock_redis

def verify_user(username, password):
    """Verifies user credentials against the database (real or mock)."""
    redis = get_redis_client()
    if not redis:
        st.error("Redis connection is not available.")
        return False

    user_key = f"user:{username}"
    if not redis.exists(user_key):
        return False

    user_data = redis.hgetall(user_key)
    if not user_data:
        return False

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == user_data.get("password_hash")

def seed_admin_user():
    """
    Seeds the database with a default admin user if one doesn't exist.
    Works with both real and mock Redis.
    """
    redis = get_redis_client()
    if not redis:
        st.warning("Cannot seed admin user: Redis client is not available.")
        return

    admin_key = "user:admin"
    if not redis.exists(admin_key):
        print("Admin user not found, creating one.")
        password = "admin123"
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        redis.hset(admin_key, "username", "admin")
        redis.hset(admin_key, "password_hash", password_hash)
        redis.hset(admin_key, "role", "doctor")
        print("Default admin user created/seeded.")

if __name__ == '__main__':
    seed_admin_user()
