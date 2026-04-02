import os
import sys

# --- STREAMLIT CLOUD SQLITE PATCH ---
# Streamlit Community Cloud runs an older Debian Linux with SQLite < 3.35.
# ChromaDB 0.4+ uses Rust bindings that require modern SQLite "RETURNING" syntax. 
# We MUST forcefully hot-swap the system SQLite engine with pysqlite3-binary before importing chromadb!
if os.path.exists("/mount/src") or os.environ.get("FIREBASE_JSON_STRING"):
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb
from chromadb.utils import embedding_functions

# Local folder where data will be stored.
# Streamlit Cloud's network-mounted containers (/mount/src) don't support strict SQLite WAL file locks, 
# resulting in 'InternalError' exactly when adding vectors. Redirecting to /tmp fixes this instantly!
if os.path.exists("/mount/src") or os.environ.get("FIREBASE_JSON_STRING"):
    PERSIST_DIR = "/tmp/chroma_store"
else:
    PERSIST_DIR = "./data/chroma_store"

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=PERSIST_DIR)

# Embedding function
embedding_function = embedding_functions.DefaultEmbeddingFunction()

# Create collection for RAG context
collection = client.get_or_create_collection(
    name="retail_memory", 
    embedding_function=embedding_function
)

# Create collection specifically for ordered Chat History
chat_collection = client.get_or_create_collection(
    name="chat_history",
    embedding_function=embedding_function
)

import time

def add_chat_message(user_id: str, session_id: str, role: str, text: str):
    """Log a structured message directly into the chat history collection."""
    timestamp = time.time()
    msg_id = f"hist_{session_id}_{timestamp}_{hash(text)}"
    chat_collection.add(
        documents=[text],
        metadatas=[{"user_id": user_id, "session_id": session_id, "role": role, "timestamp": timestamp}],
        ids=[msg_id]
    )

def get_chat_history(user_id: str, session_id: str):
    """Retrieve and order the full chat history for a given session."""
    results = chat_collection.get(
        where={"$and": [{"user_id": user_id}, {"session_id": session_id}]},
        include=["documents", "metadatas"]
    )
    
    if not results or not results.get("documents"):
        return []
        
    doc_meta_pairs = list(zip(results["documents"], results["metadatas"]))
    doc_meta_pairs.sort(key=lambda x: x[1].get("timestamp", 0) if x[1] else 0)
    
    history = []
    for doc, meta in doc_meta_pairs:
        if meta and "role" in meta:
            history.append({
                "role": meta["role"],
                "content": doc
            })
    return history

def get_user_sessions(user_id: str):
    """Retrieve all distinct session IDs and their starting timestamp for a user."""
    results = chat_collection.get(
        where={"user_id": user_id},
        include=["metadatas", "documents"]
    )
    if not results or not results.get("metadatas"):
        return []

    sessions = {}
    for meta, doc in zip(results["metadatas"], results["documents"]):
        if not meta or "session_id" not in meta:
            continue
        sid = meta["session_id"]
        ts = meta.get("timestamp", 0)
        
        # Track the first message (earliest timestamp)
        if sid not in sessions:
            sessions[sid] = {"timestamp": ts, "first_msg": doc if meta.get("role")=="user" else "New Chat"}
        else:
            if ts < sessions[sid]["timestamp"]:
                sessions[sid]["timestamp"] = ts
                if meta.get("role") == "user":
                    sessions[sid]["first_msg"] = doc
                    
    # Sort sessions by timestamp descending (newest first)
    sorted_sessions = sorted(sessions.items(), key=lambda x: x[1]["timestamp"], reverse=True)
    
    ret = []
    for sid, data in sorted_sessions:
        title = data["first_msg"]
        if len(title) > 25:
            title = title[:25] + "..."
        ret.append({"session_id": sid, "title": title, "timestamp": data["timestamp"]})
    return ret

def delete_chat_session(user_id: str, session_id: str):
    """Delete a specific chat session safely from ChromaDB."""
    chat_collection.delete(
        where={"$and": [{"user_id": user_id}, {"session_id": session_id}]}
    )

def delete_all_chat_sessions(user_id: str):
    """Purge all chat sessions absolutely for a user from ChromaDB."""
    chat_collection.delete(
        where={"user_id": user_id}
    )


# Add user id to memory
def add_memory(user_id, text:str):
    collection.add(
        documents=[text],
        metadatas=[{"user_id": user_id}],
        ids=[f"{user_id}_{hash(text)}"]
    )
# Search user memory
def search_memory(user_id, query:str, n_results:int=5):
    results = collection.query(
        query_texts=[query],
        where={"user_id": user_id},
        n_results=n_results
    )
    if results["documents"]:
        return results["documents"][0]
    return []

# Get all memories for a user
def get_all_memories(user_id):
    results = collection.get(
        where={"user_id": user_id}
    )
    if results["documents"]:
        return results["documents"][0]
    return []

# Delete all memories for a user
def delete_all_memories(user_id):
    collection.delete(
        where={"user_id": user_id}
    )

# Update a memory
def update_memory(user_id, text:str):
    collection.update(
        documents=[text],
        metadatas=[{"user_id": user_id}],
        ids=[f"{user_id}_{hash(text)}"]
    )


if __name__ == "__main__":
    add_memory("user1", "I like blue color")
    add_memory("user2", "I like red color")
    add_memory("user3", "I like green color")
    print(search_memory("user1", "What color do I like?"))
    print(search_memory("user2", "What color do I like?"))
    print(search_memory("user3", "What color do I like?"))
    #print(get_all_memories("user1"))
    # update_memory("user1", "I like yellow color")
    # print(search_memory("user1", "What color do I like?"))
    # delete_all_memories("user1")
    # print(get_all_memories("user1"))    