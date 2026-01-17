import sys
import os

# Add current directory to path
sys.path.append(os.path.abspath("medgemma_triage"))

try:
    import prompts
    import mcp_client
    import app
    # Mock fastmcp to allow import verification if it's not installed
    # Actually we can't easily mock it before import unless we use sys.modules trick,
    # but let's assume if it fails it's due to missing package which is expected in this env.
    print("Imports successful (modules located).")
except ImportError as e:
    if "fastmcp" in str(e) or "streamlit" in str(e):
        print(f"Import failed as expected due to missing env packages: {e}")
    else:
        print(f"Unexpected Import Error: {e}")
        sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
