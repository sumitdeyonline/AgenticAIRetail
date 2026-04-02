import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Load environment variables from .env
load_dotenv()
from chromadb.utils import embedding_functions

# Reuse the same local embedding function used by ChromaDB (all-MiniLM-L6-v2) to avoid needing extra keys
embedder = embedding_functions.DefaultEmbeddingFunction()

def get_pinecone_index(index_name="retail-data"):
    """Initialize and retrieve the Pinecone index."""
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable is missing.")
        
    pc = Pinecone(api_key=api_key)
    
    # Check if index exists, create if not
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Index '{index_name}' not found. Creating a new Serverless index...")
        pc.create_index(
            name=index_name,
            dimension=384, # Output dimension for all-MiniLM-L6-v2
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1' # Default serverless region
            )
        )
    return pc.Index(index_name)

def populate_pinecone_data():
    """Seed the Pinecone index with initial dummy retail inventory and order statuses."""
    index = get_pinecone_index()
    
    # Raw Data
    inventory = [
        {"id": "inv_laptop", "text": "laptop", "metadata": {"type": "inventory", "product": "laptop", "stock": 15}},
        {"id": "inv_headphones", "text": "headphones", "metadata": {"type": "inventory", "product": "headphones", "stock": 100}},
        {"id": "inv_keyboard", "text": "keyboard", "metadata": {"type": "inventory", "product": "keyboard", "stock": 36}},
        {"id": "inv_monitor", "text": "monitor", "metadata": {"type": "inventory", "product": "monitor", "stock": 5}},
        {"id": "inv_mouse", "text": "mouse", "metadata": {"type": "inventory", "product": "mouse", "stock": 20}}
    ]
    
    orders = [
        {"id": "ord_1", "text": "ORD-12345", "metadata": {"type": "order", "order_id": "ORD-12345", "status": "Processing - will ship in 1-2 business days."}},
        {"id": "ord_2", "text": "ORD-67890", "metadata": {"type": "order", "order_id": "ORD-67890", "status": "Shipped - currently in transit and will arrive soon."}},
        {"id": "ord_3", "text": "ORD-99999", "metadata": {"type": "order", "order_id": "ORD-99999", "status": "Delivered - package was successfully delivered to the destination."}}
    ]
    
    all_items = inventory + orders
    texts = [item["text"] for item in all_items]
    
    print("Embedding data...")
    embeddings = embedder(texts)
    
    vectors = []
    for i, item in enumerate(all_items):
        vectors.append({
            "id": item["id"],
            "values": [float(x) for x in embeddings[i]],
            "metadata": item["metadata"]
        })
        
    print(f"Upserting {len(vectors)} vectors into Pinecone...")
    index.upsert(vectors=vectors)
    print("Pinecone data seeded successfully!")

def query_pinecone(query_text: str, filter_type: str):
    """Query Pinecone for similarity search and return top metadata matching the type filter."""
    try:
        index = get_pinecone_index()
    except ValueError:
        return None # Graceful fallback if no API key is provided yet
        
    raw_vector = embedder([query_text])[0]
    query_vector = [float(x) for x in raw_vector]
    
    results = index.query(
        vector=query_vector,
        top_k=1,
        include_metadata=True,
        filter={"type": filter_type}
    )
    
    # Return match only if confident
    if results.matches and results.matches[0].score > 0.6:
        return results.matches[0].metadata
    return None

if __name__ == "__main__":
    populate_pinecone_data()
