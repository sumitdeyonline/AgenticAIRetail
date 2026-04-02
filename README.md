# 🛍️ Agentic AI Retail Assistant

A fully production-ready, agentic retail assistant built with **LangGraph**, **Streamlit**, and the **Model Context Protocol (MCP)**. This intelligent agent orchestrates multiple cloud and local databases dynamically to answer customer queries regarding inventory, order status, and live dynamic promotions.

## 🌟 Key Features

- **Agentic Orchestration**: Powered by **LangGraph**, the AI agent dynamically plans and executes reasoning loops over multiple conversational turns, seamlessly connecting semantic intent to the right databases.
- **MCP Extensibility**: Uses a standalone Model Context Protocol (MCP) server subprocess (`mcp_server.py`) to dynamically hook into a external cloud-based Google Firebase database for real-time promotional logic.
- **Cloud Vector DB**: Queries **Pinecone** in real-time to rapidly search massive product catalogs and answer complex semantic questions about warehouse inventory and order shipment statuses.
- **Local Embedded Memory**: Uses **ChromaDB** locally to natively log discrete conversational histories per session and embed user preference memories for semantic cross-session RAG context.
- **Sleek Streamlit UI**: Offers a beautiful, multi-session Streamlit layout mimicking standard modern web topologies. Achieves blazing-fast seamless session recovery using pure Markdown URL parameter routing (hyperlinking) to completely bypass UI blocking.
- **Cost Analytics**: Features a custom-built asynchronous streaming tracker to cleanly log token usage and exactly estimate LLM inference costs per request in real-time on the sidebar!

## 🏗️ Architecture

You can immediately view the full system data flow and component diagram:
![Architecture Diagram](./architecture.png)

1. **Frontend**: The `app.py` process renders standard Streamlit components, utilizing raw Markdown anchor links routing through URL parameters for instant session resumption without page flickering.
2. **Memory Store**: `memory/chroma_store.py` maintains local disk persistence, routing general chats into `chat_history` for exact recall, and embedding preferences into a `retail_memory` semantic collection.
3. **Cloud Database Connectors**: `agent/tools.py` intercepts agent decisions and fires direct embedded vector lookups to Pinecone.
4. **MCP Layer**: `agent/mcp_server.py` listens to the LangGraph brain asynchronously and translates tool execution commands directly into Firestore NoSQL queries!

## 🚀 Quickstart Installation

### 1. Clone & Install Dependencies
This project uses `uv` for lightning-fast deterministic environment management.
```bash
uv sync
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory (you can base it off of `.env.example`).
```env
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key

# Download your Firebase Admin SDK Service Account JSON key
FIREBASE_CREDENTIALS_PATH=firebase-key.json

# Optional: Enable full LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langchain_key
```

### 3. Provide Firebase Credentials

**For Local Development:**
Download your Google Firebase Admin SDK `.json` private key, rename it to `firebase-key.json`, and place it physically in the absolute root folder. *(Note: This file is automatically `.gitignored` for safety)*.

**For Cloud Deployment (Streamlit Cloud / Hugging Face Spaces):**
Because `firebase-key.json` is perfectly `.gitignored` to prevent catastrophic credential leaks, standard cloud deployments will never see this file. 
Instead, we use **Environment Secrets**:
1. Open your downloaded `firebase-key.json` inside a text editor.
2. Copy its entire multiline JSON string contents.
3. Paste that entire string directly into your Cloud Provider's Secrets panel (e.g. *Streamlit Community Cloud Secrets* `secrets.toml`, or *Hugging Face Spaces Environment Variables*) under exactly this variable name:
```env
FIREBASE_JSON_STRING="..."
```
The application's backend scripts automatically detect this master cloud secret on startup and will dynamically parse the JSON directly from memory without ever needing a physical local file!

### 4. Seed the Databases (First Time Only)
Before talking to the agent, populate your Pinecone vectors and Firebase directories with sample store data:
```bash
uv run python utils/pinecone_store.py
uv run python utils/firebase_store.py
```

### 5. Run the AI Assistant
Boot up the Streamlit UI and talk to your local AI agent orchestrator!
```bash
uv run streamlit run app.py
```

## 🛠️ Stack & Technologies
- **LangChain / LangGraph** (Agent Framework orchestrating thought loops)
- **Model Context Protocol (MCP)** (Agentic Tool Server Standard standardizing Cloud API tools)
- **Groq** (Blazing Fast LPU Inference `llama-3.3-70b-versatile` base model)
- **ChromaDB** (Local Memory/History SQLite Vector persistence)
- **Pinecone** (Cloud Vector Database optimized for product catalog search)
- **Google Firebase Firestore** (Cloud Document DB for instant promotional syncing)
- **Streamlit** (UI / Frontend Engine optimized for rapid Python AI development)
- **uv** (Modern, rapid Python Environment Manager)
