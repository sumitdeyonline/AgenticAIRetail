import os
import sys

# Need to append root path so memory.chroma_store resolves
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import RETAIL_TOOLS
from memory.chroma_store import search_memory, add_memory


def create_agent_graph(mcp_tools: list, provider: str = "openai"):
    """Initialize the compiled state graph for the retail agent."""
    
    all_tools = RETAIL_TOOLS + mcp_tools
    
    if provider == "groq":
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    else:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
    bound_llm = llm.bind_tools(all_tools)

    def fetch_memory_node(state: AgentState):
        """Retrieve historical context from ChromaDB for the user."""
        messages = state["messages"]
        last_msg = messages[-1].content
        
        meta = state.get("metadata", {})
        user_id = meta.get("user_id", "default_user")
        
        # Search memory (limit to top 2 results)
        retrieved_docs = search_memory(user_id, last_msg, n_results=2)
        
        # retrieved_docs is either a straight list of strings or empty based on the chroma_store implementation
        if retrieved_docs:
            context_str = " ".join(retrieved_docs)
        else:
            context_str = "No specific historical preferences found."
            
        # Add their latest query to memory casually
        add_memory(user_id, last_msg)
        
        return {"context": context_str}

    def agent_node(state: AgentState):
        """Invoke the LLM to process the question with tools and context."""
        messages = state["messages"]
        context = state.get("context", "")
        
        system_prompt = (
            "You are a helpful and polite retail assistant. You have access to user memory context "
            "as well as specialized tools for checking inventory, shipping status, and promotions.\n\n"
            f"User Context / Memory:\n{context}\n\n"
            "If the user asks about something unrelated, politely steer them back to retail inquiries."
        )
        
        sys_msg = SystemMessage(content=system_prompt)
        response = bound_llm.invoke([sys_msg] + messages)
        
        return {"messages": [response]}

    def should_continue(state: AgentState):
        """Router to check if the LLM called a tool or finished."""
        last_message = state["messages"][-1]
        
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    # Assemble Graph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("fetch_memory", fetch_memory_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(all_tools))
    
    workflow.add_edge(START, "fetch_memory")
    workflow.add_edge("fetch_memory", "agent")
    
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")
    
    app = workflow.compile()
    #print(app.get_graph().draw_ascii())
    
    return app
