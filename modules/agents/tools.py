"""
Agent Tools - Functions the AI can call to take actions.

Each tool has:
- name: Identifier for the tool
- description: What it does (shown to the LLM)
- parameters: JSON schema for inputs
- execute: Async function that runs the tool
"""

import asyncio
import json
import re
import math
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
import httpx


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None


@dataclass
class Tool:
    """Definition of an agent tool."""
    name: str
    description: str
    parameters: List[ToolParameter]
    execute: Callable[..., Awaitable[Dict[str, Any]]]
    category: str = "general"
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


class ToolRegistry:
    """Registry of available tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_builtin_tools()
    
    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required
                    }
                    for p in t.parameters
                ]
            }
            for t in self.tools.values()
        ]
    
    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI format."""
        return [t.to_openai_schema() for t in self.tools.values()]
    
    async def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name."""
        tool = self.tools.get(name)
        if not tool:
            return {"error": f"Tool '{name}' not found"}
        
        try:
            result = await tool.execute(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _register_builtin_tools(self):
        """Register built-in tools."""
        
        # ============================================
        # Calculator Tool
        # ============================================
        async def calculator(expression: str) -> Dict[str, Any]:
            """Evaluate a mathematical expression."""
            # Safe evaluation with limited functions
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "sqrt": math.sqrt,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "log": math.log, "log10": math.log10, "exp": math.exp,
                "pi": math.pi, "e": math.e
            }
            
            # Clean expression
            expression = expression.replace("^", "**")
            
            try:
                # Evaluate with restricted namespace
                result = eval(expression, {"__builtins__": {}}, allowed_names)
                return {"expression": expression, "result": result}
            except Exception as e:
                return {"error": str(e)}
        
        self.register(Tool(
            name="calculator",
            description="Evaluate mathematical expressions. Supports +, -, *, /, ^, sqrt, sin, cos, tan, log, etc.",
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="The mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)')"
                )
            ],
            execute=calculator,
            category="math"
        ))
        
        # ============================================
        # Current DateTime Tool
        # ============================================
        async def get_datetime(timezone: str = "UTC") -> Dict[str, Any]:
            """Get current date and time."""
            now = datetime.now()
            return {
                "datetime": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day_of_week": now.strftime("%A"),
                "timezone": timezone,
                "unix_timestamp": int(now.timestamp())
            }
        
        self.register(Tool(
            name="get_datetime",
            description="Get the current date and time.",
            parameters=[
                ToolParameter(
                    name="timezone",
                    type="string",
                    description="Timezone (e.g., 'UTC', 'America/New_York')",
                    required=False,
                    default="UTC"
                )
            ],
            execute=get_datetime,
            category="utility"
        ))
        
        # ============================================
        # Web Search Tool (Multi-source)
        # ============================================
        async def web_search(query: str, num_results: int = 5) -> Dict[str, Any]:
            """Search the web using multiple sources."""
            import os
            
            results = []
            search_source = "duckduckgo"
            
            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    
                    # Method 1: Try SerpAPI if key is available
                    serpapi_key = os.getenv("SERPAPI_KEY")
                    if serpapi_key:
                        try:
                            response = await client.get(
                                "https://serpapi.com/search",
                                params={
                                    "q": query,
                                    "api_key": serpapi_key,
                                    "engine": "google",
                                    "num": num_results
                                }
                            )
                            data = response.json()
                            
                            for item in data.get("organic_results", [])[:num_results]:
                                results.append({
                                    "title": item.get("title", ""),
                                    "snippet": item.get("snippet", ""),
                                    "url": item.get("link", ""),
                                    "position": item.get("position")
                                })
                            
                            if results:
                                search_source = "google_serpapi"
                        except Exception:
                            pass
                    
                    # Method 2: DuckDuckGo Lite (more reliable)
                    if not results:
                        try:
                            response = await client.post(
                                "https://lite.duckduckgo.com/lite/",
                                data={"q": query},
                                headers=headers
                            )
                            html = response.text
                            
                            # Parse lite results
                            import re
                            
                            # Find links in the lite version
                            link_pattern = r'<a[^>]*rel="nofollow"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
                            snippet_pattern = r'<td[^>]*class="result-snippet"[^>]*>([^<]+)</td>'
                            
                            links = re.findall(link_pattern, html)
                            snippets = re.findall(snippet_pattern, html)
                            
                            for i, (url, title) in enumerate(links[:num_results]):
                                if url.startswith("http") and "duckduckgo" not in url:
                                    snippet = snippets[i] if i < len(snippets) else ""
                                    results.append({
                                        "title": title.strip()[:100],
                                        "snippet": snippet.strip()[:300],
                                        "url": url
                                    })
                            
                            if results:
                                search_source = "duckduckgo_lite"
                        except Exception:
                            pass
                    
                    # Method 3: DuckDuckGo Instant Answer API (for facts/wiki)
                    if not results:
                        try:
                            response = await client.get(
                                "https://api.duckduckgo.com/",
                                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
                            )
                            data = response.json()
                            
                            if data.get("Abstract"):
                                results.append({
                                    "title": data.get("Heading", "Result"),
                                    "snippet": data["Abstract"][:500],
                                    "url": data.get("AbstractURL", ""),
                                    "source": data.get("AbstractSource", "Wikipedia")
                                })
                                search_source = "duckduckgo_instant"
                            
                            # Add related topics
                            for topic in data.get("RelatedTopics", []):
                                if isinstance(topic, dict) and topic.get("Text"):
                                    results.append({
                                        "title": topic.get("Text", "")[:80],
                                        "snippet": topic.get("Text", ""),
                                        "url": topic.get("FirstURL", "")
                                    })
                                # Handle nested topics
                                elif isinstance(topic, dict) and topic.get("Topics"):
                                    for subtopic in topic.get("Topics", [])[:2]:
                                        if subtopic.get("Text"):
                                            results.append({
                                                "title": subtopic.get("Text", "")[:80],
                                                "snippet": subtopic.get("Text", ""),
                                                "url": subtopic.get("FirstURL", "")
                                            })
                        except Exception:
                            pass
                    
                    # Method 4: Wikipedia API as fallback for factual queries
                    if not results:
                        try:
                            response = await client.get(
                                "https://en.wikipedia.org/w/api.php",
                                params={
                                    "action": "query",
                                    "list": "search",
                                    "srsearch": query,
                                    "format": "json",
                                    "srlimit": num_results
                                }
                            )
                            data = response.json()
                            
                            for item in data.get("query", {}).get("search", []):
                                # Clean snippet of HTML
                                snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                                title = item.get("title", "")
                                results.append({
                                    "title": title,
                                    "snippet": snippet[:300],
                                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                    "source": "Wikipedia"
                                })
                            
                            if results:
                                search_source = "wikipedia"
                        except Exception as wiki_err:
                            print(f"Wikipedia search error: {wiki_err}")
                    
                    if not results:
                        return {
                            "query": query,
                            "message": f"No results found for '{query}'.",
                            "suggestion": "Try different keywords or check spelling.",
                            "results": [],
                            "source": "none"
                        }
                    
                    return {
                        "query": query,
                        "num_results": len(results[:num_results]),
                        "results": results[:num_results],
                        "source": search_source
                    }
                    
            except Exception as e:
                return {"error": f"Search failed: {str(e)}", "query": query}
        
        self.register(Tool(
            name="web_search",
            description="Search the web for current information. Use this when you need up-to-date information not in your training data.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query"
                ),
                ToolParameter(
                    name="num_results",
                    type="number",
                    description="Number of results to return (default: 5)",
                    required=False,
                    default=5
                )
            ],
            execute=web_search,
            category="search"
        ))
        
        # ============================================
        # Python Code Execution Tool
        # ============================================
        async def execute_python(code: str) -> Dict[str, Any]:
            """Execute Python code in a sandboxed environment."""
            import io
            import sys
            from contextlib import redirect_stdout, redirect_stderr
            
            # Capture output
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # Restricted globals
            safe_globals = {
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "range": range,
                    "list": list,
                    "dict": dict,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "abs": abs,
                    "round": round,
                    "sorted": sorted,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "isinstance": isinstance,
                    "type": type,
                }
            }
            
            result = None
            error = None
            
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    # Execute the code
                    exec_result = exec(code, safe_globals)
                    
                    # Try to get last expression value
                    if '\n' not in code.strip() and not code.strip().startswith(('import', 'from', 'def', 'class', 'if', 'for', 'while')):
                        try:
                            result = eval(code, safe_globals)
                        except:
                            pass
                            
            except Exception as e:
                error = f"{type(e).__name__}: {str(e)}"
            
            return {
                "code": code,
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue(),
                "result": result,
                "error": error
            }
        
        self.register(Tool(
            name="execute_python",
            description="Execute Python code. Use for calculations, data processing, or generating outputs. Output is captured from print statements.",
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute"
                )
            ],
            execute=execute_python,
            category="code"
        ))
        
        # ============================================
        # URL Fetch Tool
        # ============================================
        async def fetch_url(url: str, extract_text: bool = True) -> Dict[str, Any]:
            """Fetch content from a URL."""
            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    response = await client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (compatible; GoAI/1.0)"
                    })
                    
                    content_type = response.headers.get("content-type", "")
                    
                    if "text/html" in content_type and extract_text:
                        # Basic HTML to text extraction
                        html = response.text
                        # Remove scripts and styles
                        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                        # Remove tags
                        text = re.sub(r'<[^>]+>', ' ', html)
                        # Clean whitespace
                        text = re.sub(r'\s+', ' ', text).strip()
                        
                        return {
                            "url": url,
                            "status": response.status_code,
                            "content_type": content_type,
                            "text": text[:5000]  # Limit to 5000 chars
                        }
                    else:
                        return {
                            "url": url,
                            "status": response.status_code,
                            "content_type": content_type,
                            "content": response.text[:5000]
                        }
                        
            except Exception as e:
                return {"error": f"Failed to fetch URL: {str(e)}"}
        
        self.register(Tool(
            name="fetch_url",
            description="Fetch and extract text content from a URL. Use to read web pages, articles, or documentation.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL to fetch"
                ),
                ToolParameter(
                    name="extract_text",
                    type="boolean",
                    description="Extract text from HTML (default: true)",
                    required=False,
                    default=True
                )
            ],
            execute=fetch_url,
            category="web"
        ))
        
        # ============================================
        # JSON Parser Tool
        # ============================================
        async def parse_json(json_string: str, path: str = "") -> Dict[str, Any]:
            """Parse JSON and optionally extract a path."""
            try:
                data = json.loads(json_string)
                
                if path:
                    # Navigate path like "data.users[0].name"
                    parts = re.split(r'\.|\[|\]', path)
                    parts = [p for p in parts if p]
                    
                    result = data
                    for part in parts:
                        if part.isdigit():
                            result = result[int(part)]
                        else:
                            result = result[part]
                    
                    return {"path": path, "value": result}
                
                return {"parsed": data}
                
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON: {str(e)}"}
            except (KeyError, IndexError, TypeError) as e:
                return {"error": f"Path error: {str(e)}"}
        
        self.register(Tool(
            name="parse_json",
            description="Parse JSON string and optionally extract values using a path like 'data.users[0].name'.",
            parameters=[
                ToolParameter(
                    name="json_string",
                    type="string",
                    description="JSON string to parse"
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Optional path to extract (e.g., 'data.items[0].name')",
                    required=False,
                    default=""
                )
            ],
            execute=parse_json,
            category="utility"
        ))


# Singleton registry
tool_registry = ToolRegistry()

