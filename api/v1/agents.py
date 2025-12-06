"""
Agents API - AI agents with tool-using capabilities.

Endpoints for running agents that can:
- Search the web
- Execute code
- Perform calculations
- Fetch URLs
- And more...
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio

from modules.agents import agent, tool_registry, Agent
from modules.agents.planner import plan_execute_agent, PlanAndExecuteAgent


router = APIRouter()


class AgentRequest(BaseModel):
    """Request to run an agent."""
    task: str
    context: Optional[str] = None
    model: Optional[str] = "gpt-4o-mini"
    max_iterations: Optional[int] = 5
    stream: bool = False


class PlanExecuteRequest(BaseModel):
    """Request for plan-and-execute agent."""
    task: str
    model: Optional[str] = "gpt-4o-mini"
    max_replans: Optional[int] = 2
    stream: bool = False


class ToolExecuteRequest(BaseModel):
    """Request to execute a single tool."""
    tool_name: str
    arguments: Dict[str, Any]


@router.post("/run")
async def run_agent(request: AgentRequest):
    """
    Run an AI agent on a task.
    
    The agent can use tools like:
    - web_search: Search the internet
    - calculator: Perform math calculations
    - execute_python: Run Python code
    - fetch_url: Fetch web page content
    - get_datetime: Get current date/time
    
    Example:
    ```
    POST /api/v1/agents/run
    {
        "task": "What is the current population of Tokyo and calculate 15% of it"
    }
    ```
    """
    if request.stream:
        return StreamingResponse(
            stream_agent(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    
    # Create agent with requested model
    agent_instance = Agent(
        model=request.model,
        max_iterations=request.max_iterations
    )
    
    result = await agent_instance.run(
        task=request.task,
        context=request.context
    )
    
    return {
        "answer": result.answer,
        "tools_used": result.tools_used,
        "steps": [
            {
                "state": step.state.value,
                "content": step.content[:500] + "..." if len(step.content) > 500 else step.content,
                "tool_calls": [
                    {
                        "tool": tc.tool_name,
                        "arguments": tc.arguments,
                        "result": tc.result,
                        "duration_ms": tc.duration_ms
                    }
                    for tc in step.tool_calls
                ]
            }
            for step in result.steps
        ],
        "total_tokens": result.total_tokens,
        "latency_ms": result.latency_ms,
        "model": result.model
    }


async def stream_agent(request: AgentRequest):
    """Stream agent execution."""
    agent_instance = Agent(
        model=request.model,
        max_iterations=request.max_iterations
    )
    
    async for event in agent_instance.stream(
        task=request.task,
        context=request.context
    ):
        yield f"data: {json.dumps(event)}\n\n"
        await asyncio.sleep(0)
    
    yield "data: [DONE]\n\n"


@router.get("/tools")
async def list_tools():
    """
    List all available tools.
    
    Returns information about each tool including:
    - name: Tool identifier
    - description: What the tool does
    - parameters: Required and optional inputs
    - category: Tool category
    """
    tools = tool_registry.list_tools()
    
    # Group by category
    by_category = {}
    for tool in tools:
        cat = tool["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tool)
    
    return {
        "tools": tools,
        "by_category": by_category,
        "total": len(tools)
    }


@router.post("/tools/execute")
async def execute_tool(request: ToolExecuteRequest):
    """
    Execute a single tool directly.
    
    Useful for testing tools or using them standalone.
    
    Example:
    ```
    POST /api/v1/agents/tools/execute
    {
        "tool_name": "calculator",
        "arguments": {"expression": "sqrt(144) + 10"}
    }
    ```
    """
    result = await tool_registry.execute(
        request.tool_name,
        **request.arguments
    )
    
    return {
        "tool": request.tool_name,
        "arguments": request.arguments,
        "result": result
    }


@router.post("/ask")
async def quick_ask(question: str, use_tools: bool = True):
    """
    Quick ask endpoint - simple interface for agent queries.
    
    Example: GET /api/v1/agents/ask?question=What is 15% of 847?
    """
    if use_tools:
        agent_instance = Agent(model="gpt-4o-mini", max_iterations=3)
        result = await agent_instance.run(task=question)
        
        return {
            "question": question,
            "answer": result.answer,
            "tools_used": result.tools_used
        }
    else:
        # Direct LLM call without tools
        from core.llm import llm_router
        
        response = await llm_router.run(
            model_id="gpt-4o-mini",
            messages=[{"role": "user", "content": question}]
        )
        
        return {
            "question": question,
            "answer": response.get("content", ""),
            "tools_used": []
        }


# ==================== Plan-and-Execute Agent ====================

@router.post("/plan-execute")
async def run_plan_execute(request: PlanExecuteRequest):
    """
    Run the Plan-and-Execute agent pattern.
    
    This agent:
    1. PLAN: Creates a detailed step-by-step plan
    2. EXECUTE: Runs each step, using tools as needed
    3. REPLAN: Revises the plan if steps fail
    4. SYNTHESIZE: Combines results into final answer
    
    Ideal for complex, multi-step tasks.
    
    Example:
    ```
    POST /api/v1/agents/plan-execute
    {
        "task": "Research the top 3 Python web frameworks, compare their performance, and recommend the best one for a startup"
    }
    ```
    
    Response includes:
    - goal: The understood objective
    - steps: Each planned step with status and results
    - final_result: Synthesized answer
    - replans: Number of plan revisions needed
    """
    if request.stream:
        return StreamingResponse(
            stream_plan_execute(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    
    agent_instance = PlanAndExecuteAgent(
        model=request.model,
        max_replans=request.max_replans
    )
    
    result = await agent_instance.run(task=request.task)
    return result


async def stream_plan_execute(request: PlanExecuteRequest):
    """Stream plan-and-execute agent execution."""
    agent_instance = PlanAndExecuteAgent(
        model=request.model,
        max_replans=request.max_replans
    )
    
    async for event in agent_instance.stream(task=request.task):
        yield f"data: {json.dumps(event)}\n\n"
        await asyncio.sleep(0)
    
    yield "data: [DONE]\n\n"


@router.post("/plan-only")
async def create_plan_only(task: str, model: str = "gpt-4o-mini"):
    """
    Create a plan without executing it.
    
    Useful for:
    - Previewing what the agent would do
    - Reviewing/editing a plan before execution
    - Understanding task complexity
    
    Example:
    ```
    POST /api/v1/agents/plan-only?task=Build a web scraper for news articles
    ```
    """
    agent_instance = PlanAndExecuteAgent(model=model)
    plan = await agent_instance._create_plan(task)
    
    return {
        "task": plan.task,
        "goal": plan.goal,
        "steps": [
            {
                "step_number": s.step_number,
                "description": s.description,
                "tools_needed": s.tools_needed,
                "depends_on": s.depends_on
            }
            for s in plan.steps
        ],
        "total_steps": len(plan.steps),
        "estimated_tools": list(set(
            tool for s in plan.steps for tool in s.tools_needed
        ))
    }

