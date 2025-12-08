"""
MCP Client - Connect to external MCP servers for tool access.

Enables the platform to use tools from:
- Local MCP servers (stdio)
- Remote MCP servers (HTTP/SSE)
- Cloud MCP providers

This implements the client side of the MCP protocol.
"""

import asyncio
import json
import httpx
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MCPTransport(str, Enum):
    """MCP connection transport types."""
    HTTP = "http"       # HTTP/REST based
    SSE = "sse"         # Server-Sent Events
    STDIO = "stdio"     # Standard I/O (local processes)
    WEBSOCKET = "ws"    # WebSocket


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an MCP server."""
    name: str
    url: str
    transport: MCPTransport = MCPTransport.HTTP
    api_key: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    enabled: bool = True


@dataclass
class RemoteTool:
    """Tool discovered from a remote MCP server."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server: str  # Which server provides this tool
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPClient:
    """
    Client for connecting to MCP servers and using their tools.
    
    Features:
    - Connect to multiple MCP servers
    - Discover and cache available tools
    - Execute remote tools
    - Handle authentication
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.tools: Dict[str, RemoteTool] = {}  # tool_name -> RemoteTool
        self.connected_servers: List[str] = []
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    def add_server(
        self,
        name: str,
        url: str,
        transport: MCPTransport = MCPTransport.HTTP,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Add an MCP server configuration.
        
        Args:
            name: Server identifier
            url: Server URL
            transport: Connection type
            api_key: Optional API key
            headers: Optional headers
        """
        self.servers[name] = MCPServerConfig(
            name=name,
            url=url.rstrip("/"),
            transport=transport,
            api_key=api_key,
            headers=headers or {}
        )
    
    def remove_server(self, name: str):
        """Remove a server configuration."""
        if name in self.servers:
            del self.servers[name]
            # Remove tools from this server
            self.tools = {
                k: v for k, v in self.tools.items()
                if v.server != name
            }
            if name in self.connected_servers:
                self.connected_servers.remove(name)
    
    async def connect(self, server_name: str) -> Dict[str, Any]:
        """
        Connect to an MCP server and discover its tools.
        
        Args:
            server_name: Name of configured server
            
        Returns:
            Server info and available tools
        """
        if server_name not in self.servers:
            return {"error": f"Server '{server_name}' not configured"}
        
        server = self.servers[server_name]
        
        if not server.enabled:
            return {"error": f"Server '{server_name}' is disabled"}
        
        try:
            client = await self._get_client()
            
            # Build headers
            headers = dict(server.headers)
            if server.api_key:
                headers["Authorization"] = f"Bearer {server.api_key}"
            headers["Content-Type"] = "application/json"
            
            # Get server info
            info_response = await client.get(
                f"{server.url}/mcp/info",
                headers=headers,
                timeout=server.timeout
            )
            
            if info_response.status_code != 200:
                return {
                    "error": f"Failed to connect: {info_response.status_code}",
                    "server": server_name
                }
            
            server_info = info_response.json()
            
            # Discover tools
            tools_response = await client.get(
                f"{server.url}/mcp/tools",
                headers=headers,
                timeout=server.timeout
            )
            
            if tools_response.status_code != 200:
                return {
                    "error": f"Failed to get tools: {tools_response.status_code}",
                    "server": server_name,
                    "server_info": server_info
                }
            
            tools_data = tools_response.json()
            
            # Register discovered tools
            discovered_tools = []
            for tool in tools_data.get("tools", []):
                remote_tool = RemoteTool(
                    name=f"{server_name}/{tool['name']}",  # Namespace tools
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                    server=server_name,
                    metadata=tool.get("metadata", {})
                )
                self.tools[remote_tool.name] = remote_tool
                discovered_tools.append({
                    "name": remote_tool.name,
                    "description": remote_tool.description
                })
            
            if server_name not in self.connected_servers:
                self.connected_servers.append(server_name)
            
            return {
                "connected": True,
                "server": server_name,
                "server_info": server_info,
                "tools_discovered": len(discovered_tools),
                "tools": discovered_tools
            }
            
        except httpx.ConnectError as e:
            return {
                "error": f"Connection failed: {str(e)}",
                "server": server_name
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "server": server_name
            }
    
    async def connect_all(self) -> Dict[str, Any]:
        """Connect to all configured servers."""
        results = {}
        for server_name in self.servers:
            result = await self.connect(server_name)
            results[server_name] = result
        
        return {
            "results": results,
            "total_servers": len(self.servers),
            "connected": len(self.connected_servers),
            "total_tools": len(self.tools)
        }
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool on a remote MCP server.
        
        Args:
            tool_name: Tool name (format: server_name/tool_name)
            arguments: Tool arguments
            timeout: Optional timeout override
            
        Returns:
            Execution result
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        tool = self.tools[tool_name]
        server = self.servers.get(tool.server)
        
        if not server:
            return {
                "success": False,
                "error": f"Server '{tool.server}' not configured"
            }
        
        # Extract actual tool name (remove server prefix)
        actual_tool_name = tool_name.split("/", 1)[1] if "/" in tool_name else tool_name
        
        try:
            client = await self._get_client()
            
            headers = dict(server.headers)
            if server.api_key:
                headers["Authorization"] = f"Bearer {server.api_key}"
            headers["Content-Type"] = "application/json"
            
            response = await client.post(
                f"{server.url}/mcp/execute",
                json={
                    "name": actual_tool_name,
                    "arguments": arguments
                },
                headers=headers,
                timeout=timeout or server.timeout
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Execution failed: {response.status_code}",
                    "response": response.text
                }
            
            result = response.json()
            
            return {
                "success": result.get("success", True),
                "result": result.get("result"),
                "error": result.get("error"),
                "server": tool.server,
                "tool": actual_tool_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "server": tool.server,
                "tool": actual_tool_name
            }
    
    def list_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all discovered tools.
        
        Args:
            server_name: Optional filter by server
            
        Returns:
            List of tool definitions
        """
        tools = []
        for name, tool in self.tools.items():
            if server_name and tool.server != server_name:
                continue
            tools.append({
                "name": name,
                "description": tool.description,
                "server": tool.server,
                "input_schema": tool.input_schema
            })
        return tools
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """List all configured servers."""
        return [
            {
                "name": s.name,
                "url": s.url,
                "transport": s.transport.value,
                "enabled": s.enabled,
                "connected": s.name in self.connected_servers,
                "tools_count": sum(
                    1 for t in self.tools.values() if t.server == s.name
                )
            }
            for s in self.servers.values()
        ]
    
    async def disconnect(self, server_name: str):
        """Disconnect from a server."""
        if server_name in self.connected_servers:
            self.connected_servers.remove(server_name)
        
        # Remove tools from this server
        self.tools = {
            k: v for k, v in self.tools.items()
            if v.server != server_name
        }
        
        return {"disconnected": server_name}
    
    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
mcp_client = MCPClient()

# Pre-configure some common MCP servers (disabled by default)
# Users can enable these by calling mcp_client.servers["name"].enabled = True

# Example: Claude's computer use tools
# mcp_client.add_server(
#     name="anthropic-tools",
#     url="https://api.anthropic.com/mcp",
#     api_key=os.getenv("ANTHROPIC_API_KEY")
# )


