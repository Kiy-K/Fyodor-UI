import sys
import os
sys.path.append(os.getcwd())

from medgemma_triage import tools, utils

print("Imports successful")
print(f"Has call_mcp_tool: {hasattr(tools, 'call_mcp_tool')}")
print(f"Has parse_medgemma_response: {hasattr(utils, 'parse_medgemma_response')}")
