import sys
import traceback

try:
    import os
    import asyncio
    import json
    import logging
    from dotenv import load_dotenv

    import firebase_admin
    from firebase_admin import credentials, firestore
    from mcp.server.models import InitializationOptions
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    import mcp.server.stdio

    load_dotenv()
    # CRITICAL: Streamlit Cloud dynamically captures stdout/stderr which breaks pure JSON-RPC! 
    # We MUST suppress all non-critical logging to prevent protocol corruption during startup.
    logging.basicConfig(level=logging.CRITICAL, stream=sys.stderr)
    logger = logging.getLogger("mcp-retail-server")

    # Basic MCP server for retail
    server = Server("retail-promotions-server")

except Exception as e:
    with open("/tmp/mcp_crash.txt", "w") as f:
        f.write("IMPORT ERROR:\n" + traceback.format_exc())
    sys.exit(1)

def get_firestore_client():
    """Initialize Firebase Admin SDK lazily and return the Firestore client."""
    if not firebase_admin._apps:
        # First, attempt to load raw JSON from cloud environment secrets (HuggingFace / Streamlit Cloud)
        firebase_secret = os.environ.get("FIREBASE_JSON_STRING")
        if firebase_secret:
            try:
                cred_dict = json.loads(firebase_secret)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                return firestore.client()
            except Exception as e:
                logger.warning(f"Failed to parse FIREBASE_JSON_STRING format: {e}")
                
        # Second, fallback to physical local machine path
        cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
        if not cred_path or not os.path.exists(cred_path):
            logger.warning(f"Firebase Credentials not found at '{cred_path}'. Returning None.")
            return None
            
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        
    return firestore.client()

def fetch_promo_from_db(location: str) -> str:
    """Synchronously fetch promotion data from Firestore."""
    db = get_firestore_client()
    if not db:
        return "PROMO: (Database offline) 5% off everything."
        
    promos_ref = db.collection("promotions")
    query = promos_ref.where("location", "==", location.lower()).limit(1)
    docs = query.stream()
    
    for doc in docs:
        data = doc.to_dict()
        return f"PROMO: {data.get('details', 'No details available.')}"
        
    # Fallback to online default if specific city lacks a promo
    if location.lower() != "online":
        return fetch_promo_from_db("online")
        
    return "No active promotions found."

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Provide a list of tools supported by this MCP server."""
    return [
        types.Tool(
            name="get_store_promotions",
            description="Get the current actively running promotions or discounts in retail stores.",
            inputSchema={
                "type": "object",
                "properties": {
                    "store_location": {
                        "type": "string",
                        "description": "City or location of the store (e.g. 'New York', 'Online')"
                    }
                },
                "required": ["store_location"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Execute a tool request from the client."""
    if name == "get_store_promotions":
        location = arguments.get("store_location", "Online") if arguments else "Online"
        
        # Async wrap the Firestore sync call to prevent blocking the MCP event loop
        loop = asyncio.get_running_loop()
        promo = await loop.run_in_executor(None, fetch_promo_from_db, location)
            
        return [
            types.TextContent(
                type="text",
                text=promo
            )
        ]
        
    raise ValueError(f"Unknown tool: {name}")

async def main():
    logger.info("Starting retail MCP server...")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="retail-promotions-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        with open("/tmp/mcp_crash.txt", "w") as f:
            f.write("RUNTIME ERROR:\n" + traceback.format_exc())
        sys.exit(1)
