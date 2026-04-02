# Agentic Retail Assistant 🛍️

## Overview
The **Agentic Retail Assistant** is a state-of-the-art AI orchestration platform built to handle complex retail interactions gracefully. The system utilizes real-time Retrieval-Augmented Generation (RAG) to seamlessly manage product inventories, while simultaneously talking to massive transactional databases to execute customer orders and track regional promotions.

By operating its tools inside an isolated **Model Context Protocol (MCP)** server subprocess, the application is fundamentally engineered for robust security and cloud-native deployments.

---

## 🏗️ Architectural Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Orchestration Brain** | LangGraph & LangChain | Manages logical reasoning, looping state, and dynamic tool selection. |
| **Frontend UI** | Streamlit | Provides the web interface, URL routing, and multi-session architecture. |
| **Catalog Memory (RAG)** | Pinecone Serverless | Handles lightning-fast vector searches across vast product catalogues. |
| **Session Memory (RAG)** | ChromaDB | Maintains segregated user chat histories and local vector indexes. |
| **Transactional DB** | Google Firebase Firestore | Securely reads and writes critical customer orders and current promotions. |
| **Tool Execution Layer** | Model Context Protocol (MCP) | Fully isolates API credentials resulting in highly resilient Cloud deployments. |

---

## 🛠️ Codebase Structure

The project has been aggressively modularized to separate concerns:

- **`app.py`**: The main execution loop. It handles the Streamlit rendering, multi-session logic (using query parameters for URL routing), and UI telemetry rendering.
- **`agent/graph.py`**: Compiles the LangGraph orchestration. This defines the exact flow between the LLM node and the `ToolNode`.
- **`agent/mcp_server.py`**: A dedicated Python subprocess file running the MCP standard. It specifically encapsulates the `firebase_admin` libraries so errors or credentials never bleed into the main AI application.
- **`agent/mcp_client.py`**: Bridges the Streamlit asyncio event loops securely to the MCP server.
- **`agent/tools.py`**: General un-isolated tools such as the `search_product_catalog` Pinecone vector lookup.
- **`utils/firebase_store.py` & `memory/chroma_store.py`**: Deep data-engine adapters. (ChromaDB uses dynamic fallback detection to use `EphemeralClient()` strictly while executing in Cloud environments to bypass old Linux SQLite lock bugs).

---

## ☁️ Cloud Deployment Mechanics

Deploying complex subprocess orchestration traditionally causes major environment errors on restrictive Cloud platforms (like Hugging Face Spaces or Streamlit Community Cloud). As such, this build enforces extreme deployment countermeasures:

1. **Lockfile Caching Bypass:**
   Because the project dependencies rely heavily on continuous integration (`pyproject.toml` managed by `uv.lock`), ensuring dependencies (e.g., `firebase-admin>=6.2.0`) are rigidly locked in `uv.lock` is mandatory.
2. **Subprocess Silence:**
   The `mcp_server.py` initializes by passing specific flags natively straight into Python (`python -W ignore`) to completely annihilate stealth Python deprecation warnings from destroying standard JSON-RPC data pipes over standard output.
3. **Ghost Secret Injection Bridge:**
   Cloud platforms like Streamlit physically isolate their secrets into Proxy objects (like `st.secrets`) rather than the native OS. The `app.py` enforces a custom "Streamlit Cloud Secret Bridge" to yank the `FIREBASE_JSON_STRING` violently into `os.environ` right before the server starts!
4. **Python Version Targeting:**
   By modifying the HuggingFace `README.md` YAML, the container forces Python 3.12 (as `>=3.13` natively rejects various legacy C++ packages due to uncompiled wheels for `onnxruntime`). 

---

## 🚀 How to Run Locally

Because the cloud architecture ensures native execution backwards-compatibility, running it locally is incredibly pure and lightning-fast.

1. Ensure `uv` is installed on your Mac.
2. Fill out your `.env` variables (including the physical local `FIREBASE_CREDENTIALS_PATH`).
3. Run the exact execution command:
```bash
uv run streamlit run app.py
```
