import os
import asyncio
import streamlit as st
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage

from agent.mcp_client import RetailMCPClient
from agent.graph import create_agent_graph
from utils.callbacks import TokenUsageAnalytics, TokenAnalyticsCallbackHandler

load_dotenv()

st.set_page_config(page_title="Retail Agentic Assistant", page_icon="🛍️", layout="wide")

import uuid
from memory.chroma_store import get_chat_history, add_chat_message, get_user_sessions, delete_chat_session, delete_all_chat_sessions

def load_session(session_id):
    """Hydrate the active chat interface based on the requested session_id."""
    st.session_state.session_id = session_id
    history = get_chat_history(st.session_state.user_id, session_id)
    if history:
        st.session_state.messages = []
        for msg in history:
            if msg["role"] == "user":
                st.session_state.messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                st.session_state.messages.append(AIMessage(content=msg["content"]))
    else:
        st.session_state.messages = [AIMessage(content="Hello! I am your retail assistant. How can I help you today?")]

# -- Session State Initialization --
if "user_id" not in st.session_state:
    st.session_state.user_id = "User1"

# Automatically intercept and process delete requests safely via URL
if "action" in st.query_params:
    action = st.query_params["action"]
    
    if action == "delete_all":
        delete_all_chat_sessions(st.session_state.user_id)
        st.query_params.clear()
        
        # Start completely fresh after wipe
        new_id = str(uuid.uuid4())
        st.session_state.session_id = new_id
        st.session_state.messages = [AIMessage(content="All history purged. How can I help you today?")]
        st.query_params["session_id"] = new_id
        st.rerun()
        
    elif action == "delete":
        session_to_delete = st.query_params.get("session_id")
        if session_to_delete:
            delete_chat_session(st.session_state.user_id, session_to_delete)
            st.query_params.clear()
            
            # If active session was deleted, boot up a fresh one
            if st.session_state.get("session_id") == session_to_delete:
                new_id = str(uuid.uuid4())
                st.session_state.session_id = new_id
                st.session_state.messages = [AIMessage(content="Chat history deleted. How can I help you today?")]
                st.query_params["session_id"] = new_id
                
            st.rerun()

# Intercept URL parameters to see if the user clicked a pure Markdown Hyperlink
if "session_id" in st.query_params:
    url_session = st.query_params["session_id"]
    if st.session_state.get("session_id") != url_session:
        load_session(url_session)
elif "session_id" not in st.session_state:
    load_session(str(uuid.uuid4()))

if "messages" not in st.session_state:
    load_session(st.session_state.session_id)

if "analytics" not in st.session_state:
    st.session_state.analytics = TokenUsageAnalytics()

# -- Sidebar Settings & Analytics --
with st.sidebar:
    st.header("⚙️ Settings")
    provider = st.selectbox("LLM Provider", ["openai", "groq"])
    
    st.markdown("---")
    st.header("📊 LLM Analytics")
    
    col1, col2 = st.columns(2)
    col1.metric("Total Calls", f"{st.session_state.analytics.successful_requests}")
    col2.metric("Est. Cost", f"${st.session_state.analytics.total_cost:.4f}")
    
    st.metric("Total Tokens", f"{st.session_state.analytics.total_tokens:,}")
    
    st.caption("Prompt vs Completion")
    st.progress(
        st.session_state.analytics.prompt_tokens / max(1, st.session_state.analytics.total_tokens)
    )

header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("🛍️ Retail Agentic Assistant")
    st.markdown("An AI assistant with LangGraph orchestration, ChromaDB, Pinecone, Firebase DB and MCP tools.")
    st.markdown("It will help you with your retail needs, like inventory management, order management and promotions.")
with header_col2:
    st.markdown(f"<div style='text-align:right; margin-top:25px; padding:5px 10px; background:#2e303e; border-radius:15px; font-size:0.9rem; color:#cfd4e1; box-shadow:0px 2px 4px rgba(0,0,0,0.2); display:inline-block; float:right;'>👤 <b>{st.session_state.user_id}</b></div>", unsafe_allow_html=True)

chat_col, history_col = st.columns([3, 1], gap="small")

with history_col:
    # 1. New chat is rendered as a flawless native web markdown hyperlink!
    new_uuid = str(uuid.uuid4())
    st.markdown(f"<a href='/?session_id={new_uuid}' target='_self' style='text-decoration: none; font-weight: bold; color: inherit;'>➕ New Chat</a>", unsafe_allow_html=True)
        
    st.markdown("<div style='font-size:0.9rem; color:gray; margin-top:15px; margin-bottom:6px; font-weight:bold; letter-spacing:0.5px;'>📝 CHAT HISTORY</div>", unsafe_allow_html=True)
    
    # 2. Delete Chat Hyperlinks using URL intercept action
    st.markdown(f"<a href='/?action=delete&session_id={st.session_state.session_id}' target='_self' style='text-decoration: none; font-size: 0.75rem; color: #ff6b6b; display: block; margin-bottom: 2px;' title='Permanently delete current session'>🗑️ Delete Current Session</a>", unsafe_allow_html=True)
    st.markdown(f"<a href='/?action=delete_all' target='_self' style='text-decoration: none; font-size: 0.75rem; color: #ff6b6b; display: block; margin-bottom: 12px;' title='Permanently delete ALL sessions'>🧨 Clear All History</a>", unsafe_allow_html=True)
    
    sessions = get_user_sessions(st.session_state.user_id)
    for session in sessions:
        # Strip potential markdown-breaking brackets
        btn_label = session["title"].replace("[", "").replace("]", "")
        
        if session["session_id"] == st.session_state.session_id:
            btn_label = f"<b>{btn_label}</b>"
            
        # 2. Render standard true HTML hyperlinks that route via query params silently in the SAME tab
        st.markdown(f"<a href='/?session_id={session['session_id']}' target='_self' style='text-decoration: none; color: inherit; display: block; margin-bottom: 4px;'>{btn_label}</a>", unsafe_allow_html=True)

with chat_col:
    # -- Chat UI --
    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            st.chat_message("user").write(msg.content)
        elif isinstance(msg, AIMessage) and msg.content:
            st.chat_message("assistant").write(msg.content)

# -- Chat Logic -- (Placed safely at bottom to anchor text input correctly)
if prompt := st.chat_input("Ask about inventory, orders, or promotions..."):
    # Append user message to UI immediately and database
    st.session_state.messages.append(HumanMessage(content=prompt))
    add_chat_message(st.session_state.user_id, st.session_state.session_id, "user", prompt)
    
    with chat_col:
        st.chat_message("user").write(prompt)

        # Spinner while agent thinks
        with st.chat_message("assistant"):
            with st.spinner("Thinking & Retrieving context..."):
                
                async def process_query():
                    # Launch MCP client contextually to prevent asyncio event loop closure issues
                    script_path = os.path.join(os.path.dirname(__file__), "agent", "mcp_server.py")
                    
                    async with RetailMCPClient(script_path) as mcp_client:
                        mcp_tools = await mcp_client.get_tools()
                        
                        # Compile graph
                        agent_graph = create_agent_graph(mcp_tools, provider=provider)
                        
                        # Set up state and callbacks
                        state = {
                            "messages": st.session_state.messages,
                            "metadata": {"user_id": st.session_state.user_id}
                        }
                        
                        is_groq = provider == "groq"
                        callback = TokenAnalyticsCallbackHandler(st.session_state.analytics, is_groq=is_groq)
                        
                        # Execute graph
                        response_state = await agent_graph.ainvoke(
                            state, 
                            config={"callbacks": [callback]}
                        )
                        
                        # The final response is the last message in the returned state
                        final_msg = response_state["messages"][-1]
                        return final_msg
                        
                # Run the async core
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                assistant_msg = loop.run_until_complete(process_query())
                
                # Store and display result
                st.session_state.messages.append(assistant_msg)
                add_chat_message(st.session_state.user_id, st.session_state.session_id, "assistant", assistant_msg.content)
                
                st.write(assistant_msg.content)
                st.rerun()  # Forces sidebar updates metric cleanly
