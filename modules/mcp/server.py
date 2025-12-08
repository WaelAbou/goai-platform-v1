"""
MCP Server Implementation - Expose tools via Model Context Protocol.

Implements the MCP specification for tool discovery and execution.
This allows external AI agents and LLMs to discover and use our tools
through a standardized protocol.

Protocol endpoints:
- GET  /mcp/tools       - List available tools
- POST /mcp/execute     - Execute a tool
- GET  /mcp/resources   - List available resources (documents, data)
- GET  /mcp/prompts     - List available prompt templates
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib


class MCPToolType(str, Enum):
    """Tool type classification."""
    FUNCTION = "function"      # Executes code/logic
    API = "api"                # Calls external API
    DATA = "data"              # Accesses data sources
    AI = "ai"                  # Uses AI models


@dataclass
class MCPTool:
    """MCP Tool definition following the protocol spec."""
    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema for parameters
    type: MCPToolType = MCPToolType.FUNCTION
    category: str = "general"
    requires_confirmation: bool = False  # For sensitive operations
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP protocol format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "type": self.type.value,
            "category": self.category,
            "requiresConfirmation": self.requires_confirmation,
            "metadata": self.metadata
        }


@dataclass
class MCPResource:
    """MCP Resource definition - data sources accessible to tools."""
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
            "metadata": self.metadata
        }


@dataclass
class MCPPrompt:
    """MCP Prompt template."""
    name: str
    description: str
    arguments: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments
        }


@dataclass
class MCPExecutionResult:
    """Result of tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "toolName": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "executionTimeMs": self.execution_time_ms,
            "metadata": self.metadata
        }


class MCPServer:
    """
    MCP Server that exposes tools via the Model Context Protocol.
    
    Features:
    - Automatic tool discovery from existing tool registry
    - JSON Schema generation for tool parameters
    - Execution with result streaming
    - Resource and prompt management
    - Authentication support
    """
    
    # Server info for MCP protocol
    SERVER_INFO = {
        "name": "goai-platform",
        "version": "1.0.0",
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": True,
            "logging": True
        }
    }
    
    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
        self.handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.execution_log: List[Dict[str, Any]] = []
        
        # Register built-in MCP tools
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """Register platform tools in MCP format."""
        from modules.agents.tools import tool_registry
        
        # Convert existing tools to MCP format
        for tool_info in tool_registry.list_tools():
            # Build JSON Schema from parameters
            properties = {}
            required = []
            
            for param in tool_info.get("parameters", []):
                prop = {
                    "type": self._map_type(param.get("type", "string")),
                    "description": param.get("description", "")
                }
                properties[param["name"]] = prop
                
                if param.get("required", True):
                    required.append(param["name"])
            
            input_schema = {
                "type": "object",
                "properties": properties,
                "required": required
            }
            
            mcp_tool = MCPTool(
                name=tool_info["name"],
                description=tool_info["description"],
                input_schema=input_schema,
                category=tool_info.get("category", "general")
            )
            
            self.tools[tool_info["name"]] = mcp_tool
            
            # Create handler that delegates to existing tool
            async def make_handler(name):
                async def handler(**kwargs):
                    return await tool_registry.execute(name, **kwargs)
                return handler
            
            # Use closure properly
            self.handlers[tool_info["name"]] = None  # Will be set up dynamically
    
    def _map_type(self, type_str: str) -> str:
        """Map internal types to JSON Schema types."""
        type_map = {
            "string": "string",
            "number": "number",
            "int": "integer",
            "integer": "integer",
            "bool": "boolean",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
            "list": "array"
        }
        return type_map.get(type_str.lower(), "string")
    
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable[..., Awaitable[Any]],
        tool_type: MCPToolType = MCPToolType.FUNCTION,
        category: str = "general",
        requires_confirmation: bool = False
    ):
        """
        Register a new MCP tool.
        
        Args:
            name: Tool name
            description: What the tool does
            input_schema: JSON Schema for parameters
            handler: Async function to execute
            tool_type: Type of tool
            category: Tool category
            requires_confirmation: Whether to require user confirmation
        """
        self.tools[name] = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            type=tool_type,
            category=category,
            requires_confirmation=requires_confirmation
        )
        self.handlers[name] = handler
    
    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "text/plain"
    ):
        """Register a data resource."""
        self.resources[uri] = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type
        )
    
    def register_prompt(
        self,
        name: str,
        description: str,
        arguments: List[Dict[str, str]] = None
    ):
        """Register a prompt template."""
        self.prompts[name] = MCPPrompt(
            name=name,
            description=description,
            arguments=arguments or []
        )
    
    # ==========================================
    # MCP Protocol Methods
    # ==========================================
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information (MCP initialize response)."""
        return self.SERVER_INFO
    
    def list_tools(self) -> Dict[str, Any]:
        """
        List available tools (MCP tools/list).
        
        Returns tools in MCP protocol format.
        """
        return {
            "tools": [tool.to_dict() for tool in self.tools.values()]
        }
    
    def list_resources(self) -> Dict[str, Any]:
        """
        List available resources (MCP resources/list).
        """
        return {
            "resources": [res.to_dict() for res in self.resources.values()]
        }
    
    def list_prompts(self) -> Dict[str, Any]:
        """
        List available prompts (MCP prompts/list).
        """
        return {
            "prompts": [p.to_dict() for p in self.prompts.values()]
        }
    
    async def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> MCPExecutionResult:
        """
        Execute a tool (MCP tools/call).
        
        Args:
            name: Tool name
            arguments: Tool arguments
            context: Optional execution context
            
        Returns:
            MCPExecutionResult with result or error
        """
        import time
        start_time = time.time()
        
        # Check if tool exists
        if name not in self.tools:
            return MCPExecutionResult(
                tool_name=name,
                success=False,
                result=None,
                error=f"Tool '{name}' not found"
            )
        
        tool = self.tools[name]
        
        # Check confirmation requirement
        if tool.requires_confirmation:
            if not context or not context.get("confirmed"):
                return MCPExecutionResult(
                    tool_name=name,
                    success=False,
                    result=None,
                    error="Tool requires confirmation. Set context.confirmed=true",
                    metadata={"requiresConfirmation": True}
                )
        
        try:
            # Use existing tool registry for execution
            from modules.agents.tools import tool_registry
            result = await tool_registry.execute(name, **arguments)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Log execution
            self._log_execution(name, arguments, result, execution_time)
            
            return MCPExecutionResult(
                tool_name=name,
                success=True,
                result=result,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            return MCPExecutionResult(
                tool_name=name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a resource (MCP resources/read).
        """
        if uri not in self.resources:
            return {"error": f"Resource '{uri}' not found"}
        
        resource = self.resources[uri]
        
        # Handle different resource types
        if uri.startswith("rag://"):
            # RAG document resource
            doc_id = uri.replace("rag://", "")
            from modules.rag import rag_engine
            
            # Search for document
            results = await rag_engine._retrieve(doc_id, top_k=1)
            if results:
                return {
                    "uri": uri,
                    "mimeType": resource.mime_type,
                    "content": results[0].content
                }
        
        return {
            "uri": uri,
            "mimeType": resource.mime_type,
            "content": None,
            "error": "Resource content not available"
        }
    
    def get_prompt(self, name: str, arguments: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Get a prompt template (MCP prompts/get).
        """
        if name not in self.prompts:
            return {"error": f"Prompt '{name}' not found"}
        
        prompt = self.prompts[name]
        
        # Would typically load and fill template here
        return {
            "name": name,
            "description": prompt.description,
            "arguments": prompt.arguments,
            "messages": []  # Would return filled messages
        }
    
    def _log_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        execution_time_ms: float
    ):
        """Log tool execution for analytics."""
        log_entry = {
            "id": hashlib.md5(
                f"{tool_name}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12],
            "tool": tool_name,
            "arguments": arguments,
            "result_summary": str(result)[:200] if result else None,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now().isoformat()
        }
        
        self.execution_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.execution_log) > 1000:
            self.execution_log = self.execution_log[-1000:]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        if not self.execution_log:
            return {"total_executions": 0, "by_tool": {}}
        
        by_tool: Dict[str, Dict[str, Any]] = {}
        for entry in self.execution_log:
            tool = entry["tool"]
            if tool not in by_tool:
                by_tool[tool] = {
                    "count": 0,
                    "total_time_ms": 0,
                    "avg_time_ms": 0
                }
            by_tool[tool]["count"] += 1
            by_tool[tool]["total_time_ms"] += entry["execution_time_ms"]
        
        for tool in by_tool:
            by_tool[tool]["avg_time_ms"] = (
                by_tool[tool]["total_time_ms"] / by_tool[tool]["count"]
            )
        
        return {
            "total_executions": len(self.execution_log),
            "by_tool": by_tool
        }


# Singleton instance
mcp_server = MCPServer()


