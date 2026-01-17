from openai import OpenAI
import os

def get_agent_response(user_input: str):
    """
    Connects to the backend using the v1/responses API standard.
    """
    try:
        # Assumes OPENAI_API_KEY is set in environment or handled by OpenAI() default behavior
        client = OpenAI()

        # Using the specific client.responses.create method as requested.
        # Note: 'responses' is a new/custom namespace on the client as per instructions.
        # Cleaning the URL from the prompt's markdown artifact.
        response = client.responses.create(
            model="gpt-4.1",
            tools=[
                {
                    "type": "mcp",
                    "server_label": "med-mcp",
                    "server_url": "https://med-mcp.fastmcp.app/mcp",
                    "require_approval": "never",
                },
            ],
            input=user_input, # Parameter is 'input', not 'messages'
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"
