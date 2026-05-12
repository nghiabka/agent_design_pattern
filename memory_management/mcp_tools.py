from langchain_core.tools import tool
import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Define the connection parameters to our local MCP Server
server_params = StdioServerParameters(
    command="python",
    args=["mcp_server.py"],
)

async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Helper function to connect to MCP server and call a tool."""
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Execute the tool via MCP
                result = await session.call_tool(tool_name, arguments=arguments)
                # Ensure we return a string
                if result.content and len(result.content) > 0:
                    return result.content[0].text
                return "SUCCESS"
    except Exception as e:
        return f"Error calling MCP Tool {tool_name}: {str(e)}"

@tool
def retrieve_customer_data(customer_id: str) -> str:
    """
    [MCP: Database Service]
    Retrieve customer data from the database.
    Requires customer_id (e.g., C123, C456).
    Returns a JSON string containing the customer's profile.
    """
    return asyncio.run(call_mcp_tool("retrieve_customer_data", {"customer_id": customer_id}))

@tool
def generate_marketing_image(prompt: str) -> str:
    """
    [MCP: Image Generation Service]
    Generate a personalized marketing image based on a prompt.
    Requires a detailed description prompt for the image.
    Returns the URL of the generated image.
    """
    return asyncio.run(call_mcp_tool("generate_marketing_image", {"prompt": prompt}))

@tool
def draft_email(customer_data_str: str, image_url: str) -> str:
    """
    [MCP: AI Copywriting Service]
    Draft a personalized email for the customer using their profile data and the generated image.
    Requires the customer data (as a string) and the image URL.
    Returns the drafted email content.
    """
    return asyncio.run(call_mcp_tool("draft_email", {"customer_data_str": customer_data_str, "image_url": image_url}))

@tool
def send_email(email_content: str, recipient: str) -> str:
    """
    [MCP: Mailer Service]
    Send the finalized email to the specified recipient.
    Requires the email content and the recipient's name or ID.
    Returns a success message.
    """
    return asyncio.run(call_mcp_tool("send_email", {"email_content": email_content, "recipient": recipient}))

# List of tools to bind to the Orchestrator
MCP_TOOLS = [retrieve_customer_data, generate_marketing_image, draft_email, send_email]
