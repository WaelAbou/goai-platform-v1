"""
MCP (Model Context Protocol) Server Support.

MCP is a standardized protocol for LLM tool integration, enabling:
- Standardized tool discovery
- Cross-platform tool sharing
- Local and remote tool execution
- Tool authentication and permissions

This module implements both:
- MCP Server: Expose our tools as MCP endpoints
- MCP Client: Connect to external MCP servers
"""

from .server import MCPServer, mcp_server
from .client import MCPClient, mcp_client

__all__ = [
    "MCPServer",
    "mcp_server",
    "MCPClient",
    "mcp_client"
]


