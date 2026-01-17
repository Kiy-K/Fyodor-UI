from openai import OpenAI
import os

def ask_fastmcp(user_input: str):
    """
    Connects to FastMCP Cloud using the specific OpenAI client snippet.
    """
    try:
        # Assumes OPENAI_API_KEY is set in environment or handled by OpenAI() default behavior
        client = OpenAI()

        # Using the exact snippet structure requested,
        # but correcting the Markdown URL artifact to a valid string URL
        # as per standard coding practice while keeping the logic intact.
        resp = client.responses.create(
            model="gpt-4.1",  # Keep this exact model name
            tools=[
                {
                    "type": "mcp",
                    "server_label": "med-mcp",
                    # Cleaned URL from "[url](url)" to "url"
                    "server_url": "https://med-mcp.fastmcp.app/mcp",
                    "require_approval": "never",
                },
            ],
            input=user_input,
        )
        return resp

    except Exception as e:
        return f"Error connecting to FastMCP: {str(e)}"
