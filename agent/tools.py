import os
import sys

# Ensure utils module is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.tools import tool
from utils.pinecone_store import query_pinecone

@tool
def check_inventory(product_name: str) -> str:
    """Check the inventory for a specific retail product. Use this tool when the user asks about product availability or stock."""
    product_name_lower = product_name.lower()
    
    # Query Pinecone database for inventory
    metadata = query_pinecone(product_name_lower, filter_type="inventory")
    
    if metadata:
        stock = metadata.get("stock", 0)
        product = metadata.get("product", product_name_lower)
        
        if stock > 0:
            return f"We have {stock} units of {product} in stock."
        else:
            return f"Sorry, {product} is currently out of stock."
            
    return f"We could not find {product_name} in our catalog."

@tool
def check_order_status(order_id: str) -> str:
    """Check the status of an order using its order ID. Use this tool when the user asks where their order is or its status."""
    order_id = order_id.upper()
    
    # Query Pinecone database for the order
    metadata = query_pinecone(order_id, filter_type="order")
    
    if metadata:
        status = metadata.get("status", "Status unknown.")
        oid = metadata.get("order_id", order_id)
        return f"Status for {oid}: {status}"
        
    return f"Order '{order_id}' not found or invalid."

# List of standard tools to be provided to the agent
RETAIL_TOOLS = [check_inventory, check_order_status]
