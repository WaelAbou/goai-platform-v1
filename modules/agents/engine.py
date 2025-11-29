"""
Agent Engine - AI that can use tools to accomplish tasks.

The agent:
1. Receives a task/question
2. Decides which tools to use
3. Executes tools and collects results
4. Synthesizes a final answer
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .tools import tool_registry, Tool
from core.llm import llm_router


class AgentState(Enum):
    """Agent execution state."""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    RESPONDING = "responding"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ToolCall:
    """Record of a tool call."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0


@dataclass
class AgentStep:
    """A single step in agent execution."""
    state: AgentState
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentResult:
    """Final result of agent execution."""
    answer: str
    steps: List[AgentStep]
    tools_used: List[str]
    total_tokens: int
    latency_ms: float
    model: str


class Agent:
    """
    AI Agent that can use tools to accomplish tasks.
    
    Supports:
    - Multi-step reasoning
    - Tool calling with function execution
    - Streaming progress updates
    - Error recovery
    """
    
    SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools. You can use these tools to help answer questions and complete tasks.

Available Tools:
{tools_description}

Instructions:
1. Analyze the user's request carefully
2. If you need current information or calculations, use the appropriate tool
3. You can use multiple tools if needed
4. After gathering information, provide a comprehensive answer
5. Always cite which tools you used and what information they provided

When you want to use a tool, respond with a JSON block like this:
```tool
{{"tool": "tool_name", "arguments": {{"arg1": "value1"}}}}
```

After receiving tool results, continue reasoning or provide your final answer."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_iterations: int = 5,
        temperature: float = 0.7
    ):
        self.model = model
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.tools = tool_registry
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with tool descriptions."""
        tools_desc = []
        for tool in self.tools.list_tools():
            params = ", ".join([
                f"{p['name']}: {p['type']}" + ("" if p['required'] else " (optional)")
                for p in tool['parameters']
            ])
            tools_desc.append(f"- {tool['name']}({params}): {tool['description']}")
        
        return self.SYSTEM_PROMPT.format(
            tools_description="\n".join(tools_desc)
        )
    
    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract tool calls from LLM response."""
        import re
        
        tool_calls = []
        
        # Look for ```tool blocks
        pattern = r'```tool\s*\n?(.*?)\n?```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                call = json.loads(match.strip())
                if "tool" in call:
                    tool_calls.append(call)
            except json.JSONDecodeError:
                continue
        
        # Also look for inline JSON tool calls
        inline_pattern = r'\{"tool":\s*"[^"]+",\s*"arguments":\s*\{[^}]+\}\}'
        inline_matches = re.findall(inline_pattern, content)
        
        for match in inline_matches:
            try:
                call = json.loads(match)
                if call not in tool_calls:
                    tool_calls.append(call)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    async def run(
        self,
        task: str,
        context: Optional[str] = None
    ) -> AgentResult:
        """
        Run the agent on a task.
        
        Args:
            task: The user's question or task
            context: Optional additional context
            
        Returns:
            AgentResult with answer and execution details
        """
        import time
        start_time = time.time()
        
        steps = []
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
        ]
        
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}\n\nTask: {task}"})
        else:
            messages.append({"role": "user", "content": task})
        
        tools_used = []
        total_tokens = 0
        final_answer = ""
        
        for iteration in range(self.max_iterations):
            # Get LLM response
            response = await llm_router.run(
                model_id=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            content = response.get("content", "")
            total_tokens += response.get("usage", {}).get("total_tokens", 0)
            
            # Check for tool calls
            tool_calls = self._extract_tool_calls(content)
            
            if tool_calls:
                # Execute tools
                step = AgentStep(
                    state=AgentState.TOOL_CALL,
                    content=content
                )
                
                tool_results = []
                for call in tool_calls:
                    tool_name = call.get("tool")
                    arguments = call.get("arguments", {})
                    
                    # Execute the tool
                    tool_start = time.time()
                    result = await self.tools.execute(tool_name, **arguments)
                    tool_duration = (time.time() - tool_start) * 1000
                    
                    tool_call = ToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        result=result,
                        duration_ms=tool_duration
                    )
                    step.tool_calls.append(tool_call)
                    
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
                    
                    tool_results.append({
                        "tool": tool_name,
                        "result": result
                    })
                
                steps.append(step)
                
                # Add tool results to messages
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"Tool Results:\n```json\n{json.dumps(tool_results, indent=2)}\n```\n\nContinue with your analysis or provide your final answer."
                })
            else:
                # No more tool calls - this is the final answer
                final_answer = content
                steps.append(AgentStep(
                    state=AgentState.COMPLETE,
                    content=content
                ))
                break
        
        latency_ms = (time.time() - start_time) * 1000
        
        return AgentResult(
            answer=final_answer,
            steps=steps,
            tools_used=tools_used,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            model=self.model
        )
    
    async def stream(
        self,
        task: str,
        context: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream agent execution progress.
        
        Yields events like:
        - {"type": "thinking", "content": "..."}
        - {"type": "tool_call", "tool": "...", "arguments": {...}}
        - {"type": "tool_result", "tool": "...", "result": {...}}
        - {"type": "answer", "content": "..."}
        - {"type": "done", "tools_used": [...]}
        """
        import time
        start_time = time.time()
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": task}
        ]
        
        if context:
            messages[1]["content"] = f"Context:\n{context}\n\nTask: {task}"
        
        tools_used = []
        
        for iteration in range(self.max_iterations):
            yield {"type": "thinking", "iteration": iteration + 1}
            
            # Get LLM response
            response = await llm_router.run(
                model_id=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            content = response.get("content", "")
            tool_calls = self._extract_tool_calls(content)
            
            if tool_calls:
                for call in tool_calls:
                    tool_name = call.get("tool")
                    arguments = call.get("arguments", {})
                    
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "arguments": arguments
                    }
                    
                    # Execute tool
                    result = await self.tools.execute(tool_name, **arguments)
                    
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": result
                    }
                    
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
                
                # Continue reasoning
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"Tool results received. Continue your analysis or provide your final answer."
                })
            else:
                # Final answer
                yield {"type": "answer", "content": content}
                break
        
        yield {
            "type": "done",
            "tools_used": tools_used,
            "latency_ms": (time.time() - start_time) * 1000
        }


# Default agent instance
agent = Agent()

