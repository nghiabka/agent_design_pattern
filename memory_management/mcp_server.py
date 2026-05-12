from mcp.server.fastmcp import FastMCP
import json
import time

# Khởi tạo MCP Server
mcp = FastMCP("marketing-mcp")

# Simulated database
CUSTOMER_DB = {
    "C123": {
        "name": "Alice Smith",
        "age": 28,
        "interests": ["photography", "outdoor hiking", "coffee"],
        "recent_purchase": "Mirrorless Camera"
    },
    "C456": {
        "name": "Bob Johnson",
        "age": 35,
        "interests": ["gaming", "mechanical keyboards", "energy drinks"],
        "recent_purchase": "Gaming Mouse"
    }
}

@mcp.tool()
def retrieve_customer_data(customer_id: str) -> str:
    """
    Retrieve customer data from the database.
    Requires customer_id (e.g., C123, C456).
    Returns a JSON string containing the customer's profile.
    """
    time.sleep(1) # Simulate network delay
    data = CUSTOMER_DB.get(customer_id)
    if data:
        return json.dumps(data)
    return json.dumps({"error": "Customer not found"})

@mcp.tool()
def generate_marketing_image(prompt: str) -> str:
    """
    Generate a personalized marketing image based on a prompt.
    Requires a detailed description prompt for the image.
    Returns the URL of the generated image.
    """
    time.sleep(2) # Simulate heavy processing
    # Simulated image URL
    image_id = abs(hash(prompt)) % 10000
    return f"https://cdn.example.com/marketing/img_{image_id}.png"

@mcp.tool()
def draft_email(customer_data_str: str, image_url: str) -> str:
    """
    Draft a personalized email for the customer using their profile data and the generated image.
    Requires the customer data (as a string) and the image URL.
    Returns the drafted email content.
    """
    time.sleep(1)
    
    try:
        customer_data = json.loads(customer_data_str)
        name = customer_data.get("name", "Valued Customer")
        interests = ", ".join(customer_data.get("interests", []))
    except:
        name = "Valued Customer"
        interests = "our products"

    email_draft = f"""
Subject: Special Offer Just For You, {name}!

Hi {name},

We noticed you've been loving {interests}. We thought you might like this exclusive offer we've put together just for you!

Check out our latest collection:
![Personalized Marketing Image]({image_url})

Best,
The Marketing Team
"""
    return email_draft.strip()

@mcp.tool()
def send_email(email_content: str, recipient: str) -> str:
    """
    (MOCK TOOL) Send the finalized email to the specified recipient.
    Requires the email content and the recipient's name or ID.
    Returns a success message.
    """
    time.sleep(1)
    return f"MOCK SUCCESS: Email to {recipient} was simulated and not actually sent."

if __name__ == "__main__":
    # Start the MCP Server on stdio transport
    mcp.run(transport="stdio")
