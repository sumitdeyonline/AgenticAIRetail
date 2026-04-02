import sys
import asyncio
from typing import List, Any
from contextlib import AsyncExitStack

# MCP SDK imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Langchain imports
from langchain_core.tools import StructuredTool
from pydantic import create_model, Field


def _mcp_schema_to_pydantic(model_name: str, schema: dict) -> type:
    """Dynamically build a Pydantic model from an MCP tool JSON schema."""
    fields = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    for prop_name, prop_info in properties.items():
        type_str = prop_info.get("type", "string")
        ptype = str
        if type_str == "integer": ptype = int
        elif type_str == "number": ptype = float
        elif type_str == "boolean": ptype = bool
        
        default_val = ... if prop_name in required else None
        fields[prop_name] = (ptype, Field(default=default_val, description=prop_info.get("description", "")))
        
    return create_model(model_name, **fields)


class RetailMCPClient:
    """Wrapper to maintain a connection to a local MCP subprocess and expose its tools to LangChain."""
    
    def __init__(self, script_path: str):
        self.script_path = script_path
        self._exit_stack = None
        self.session = None

    async def __aenter__(self):
        """Start the MCP server subprocess and initialize the session."""
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.script_path]
        )
        
        self._exit_stack = AsyncExitStack()
        
        # Start stdio transport
        stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        
        # Initialize session
        self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the subprocess and cleanup."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self.session = None

    async def get_tools(self) -> List[StructuredTool]:
        """Fetch MCP tools and wrap them as Langchain StructuredTools."""
        if not self.session:
            raise RuntimeError("MCP session not connected. Call connect() first.")
            
        response = await self.session.list_tools()
        langchain_tools = []
        
        for tool in response.tools:
            # Create a dynamic function mapping kwargs to MCP dictionary arguments
            # We must capture the current tool.name via default argument
            async def func(**kwargs) -> str:
                # Need to lookup tool name inside wrapper safely, but it's bound below
                pass 
                
            def make_coro(mcp_tool_name):
                async def _coro(**kwargs) -> str:
                    res = await self.session.call_tool(mcp_tool_name, arguments=kwargs)
                    if res.content:
                        return res.content[0].text
                    return "No response"
                return _coro
            
            # Generate the pydantic schema for Langchain
            args_schema = _mcp_schema_to_pydantic(f"{tool.name}Schema", tool.inputSchema)
            
            l_tool = StructuredTool.from_function(
                coroutine=make_coro(tool.name),
                name=tool.name,
                description=tool.description,
                args_schema=args_schema
            )
            langchain_tools.append(l_tool)
            
        return langchain_tools
