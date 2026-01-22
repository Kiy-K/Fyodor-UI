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

    def hset(self, key, value):
        print(f"MOCK: Setting data for '{key}'")
        if key not in self._data:
            self._data[key] = {}
        self._data[key].update(value)

# --- Redis Client Initialization ---
def get_redis_client():
    """
    Initializes and returns a connection to Upstash Redis if secrets are available,
    otherwise returns a mock client for local testing.
    """
    if hasattr(st, 'secrets') and "UPSTASH_REDIS_REST_URL" in st.secrets:
        try:
            redis = Redis(
                url=st.secrets["UPSTASH_REDIS_REST_URL"],
                token=st.secrets["UPSTASH_REDIS_REST_TOKEN"],
            )
            return redis
        except Exception as e:
            st.error(f"Failed to connect to real Redis: {e}")
            return None
    else:
        # Use mock client if secrets aren't found
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
        password = "admin" # Set a simpler password for local testing
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        redis.hset(admin_key, {
            "username": "admin",
            "password_hash": password_hash,
            "role": "doctor"
        })
        print("Default admin user created/seeded.")

if __name__ == '__main__':
    seed_admin_user()
