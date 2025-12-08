"""
MCP (Model Context Protocol) API - Tool interoperability.

Provides:
- MCP Server: Expose our tools to external AI agents
- MCP Client: Connect to and use external MCP servers

This enables standardized tool sharing between AI systems.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class MCPExecuteRequest(BaseModel):
    """Execute a tool via MCP."""
    name: str
    arguments: Dict[str, Any] = {}
    context: Optional[Dict[str, Any]] = None


class MCPServerAdd(BaseModel):
    """Add a remote MCP server."""
    name: str
    url: str
    api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class MCPRemoteExecute(BaseModel):
    """Execute a tool on a remote MCP server."""
    tool_name: str = Field(..., description="Format: server_name/tool_name")
    arguments: Dict[str, Any] = {}


# ============================================
# MCP Server Endpoints (Expose our tools)
# ============================================

@router.get("/info")
async def get_server_info():
    """
    Get MCP server information.
    
    Returns server capabilities and protocol version.
    """
    from modules.mcp import mcp_server
    return mcp_server.get_server_info()


@router.get("/tools")
async def list_mcp_tools():
    """
    List all available tools in MCP format.
    
    External AI agents can use this to discover our tools.
    """
    from modules.mcp import mcp_server
    return mcp_server.list_tools()


@router.post("/execute")
async def execute_mcp_tool(request: MCPExecuteRequest):
    """
    Execute a tool via MCP protocol.
    
    Example:
    ```
    POST /api/v1/mcp/execute
    {
        "name": "calculator",
        "arguments": {"expression": "2 + 2"}
    }
    ```
    """
    from modules.mcp import mcp_server
    
    result = await mcp_server.execute_tool(
        name=request.name,
        arguments=request.arguments,
        context=request.context
    )
    
    return result.to_dict()


@router.get("/resources")
async def list_mcp_resources():
    """
    List available data resources.
    """
    from modules.mcp import mcp_server
    return mcp_server.list_resources()


@router.get("/resources/{uri:path}")
async def read_mcp_resource(uri: str):
    """
    Read a specific resource.
    """
    from modules.mcp import mcp_server
    return await mcp_server.read_resource(uri)


@router.get("/prompts")
async def list_mcp_prompts():
    """
    List available prompt templates.
    """
    from modules.mcp import mcp_server
    return mcp_server.list_prompts()


@router.get("/prompts/{name}")
async def get_mcp_prompt(name: str, arguments: Optional[str] = None):
    """
    Get a prompt template.
    """
    from modules.mcp import mcp_server
    import json
    
    args = json.loads(arguments) if arguments else {}
    return mcp_server.get_prompt(name, args)


@router.get("/stats")
async def get_mcp_stats():
    """
    Get tool execution statistics.
    """
    from modules.mcp import mcp_server
    return mcp_server.get_execution_stats()


# ============================================
# MCP Client Endpoints (Use external tools)
# ============================================

@router.get("/client/servers")
async def list_remote_servers():
    """
    List configured remote MCP servers.
    """
    from modules.mcp import mcp_client
    return {
        "servers": mcp_client.list_servers(),
        "connected": len(mcp_client.connected_servers)
    }


@router.post("/client/servers")
async def add_remote_server(server: MCPServerAdd):
    """
    Add a remote MCP server configuration.
    
    Example:
    ```
    POST /api/v1/mcp/client/servers
    {
        "name": "my-tools",
        "url": "https://my-mcp-server.com",
        "api_key": "sk-..."
    }
    ```
    """
    from modules.mcp import mcp_client
    
    mcp_client.add_server(
        name=server.name,
        url=server.url,
        api_key=server.api_key,
        headers=server.headers
    )
    
    return {
        "message": f"Server '{server.name}' added",
        "server": server.name,
        "url": server.url
    }


@router.delete("/client/servers/{server_name}")
async def remove_remote_server(server_name: str):
    """
    Remove a remote MCP server.
    """
    from modules.mcp import mcp_client
    
    mcp_client.remove_server(server_name)
    
    return {"message": f"Server '{server_name}' removed"}


@router.post("/client/connect/{server_name}")
async def connect_to_server(server_name: str):
    """
    Connect to a remote MCP server and discover its tools.
    """
    from modules.mcp import mcp_client
    
    result = await mcp_client.connect(server_name)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/client/connect-all")
async def connect_to_all_servers():
    """
    Connect to all configured remote servers.
    """
    from modules.mcp import mcp_client
    return await mcp_client.connect_all()


@router.get("/client/tools")
async def list_remote_tools(server: Optional[str] = None):
    """
    List tools from connected remote servers.
    """
    from modules.mcp import mcp_client
    
    tools = mcp_client.list_tools(server_name=server)
    
    return {
        "tools": tools,
        "total": len(tools),
        "server_filter": server
    }


@router.post("/client/execute")
async def execute_remote_tool(request: MCPRemoteExecute):
    """
    Execute a tool on a remote MCP server.
    
    Example:
    ```
    POST /api/v1/mcp/client/execute
    {
        "tool_name": "my-tools/calculator",
        "arguments": {"expression": "2 + 2"}
    }
    ```
    """
    from modules.mcp import mcp_client
    
    result = await mcp_client.execute(
        tool_name=request.tool_name,
        arguments=request.arguments
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/client/disconnect/{server_name}")
async def disconnect_from_server(server_name: str):
    """
    Disconnect from a remote server.
    """
    from modules.mcp import mcp_client
    return await mcp_client.disconnect(server_name)


