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
from modules.agents.templates import (
    TEMPLATES, 
    list_templates, 
    get_template, 
    get_categories,
    create_agent_from_template,
    AgentPattern
)
from core.llm import llm_router


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


# ==================== Agent Templates ====================

class TemplateRunRequest(BaseModel):
    """Request to run an agent using a template."""
    task: str
    template_id: str
    model: Optional[str] = None  # Override template default
    temperature: Optional[float] = None
    stream: bool = False


@router.get("/templates")
async def list_agent_templates(category: str = None):
    """
    List all available agent templates.
    
    Templates are pre-configured agents for common use cases like:
    - Research and analysis
    - Code review and generation
    - Content writing
    - Customer support
    - Data analysis
    - Project planning
    
    Example:
    ```
    GET /api/v1/agents/templates
    GET /api/v1/agents/templates?category=development
    ```
    """
    templates = list_templates(category)
    categories = get_categories()
    
    return {
        "templates": templates,
        "total": len(templates),
        "categories": categories,
        "filter_applied": category
    }


@router.get("/templates/categories")
async def list_template_categories():
    """
    List available template categories.
    """
    categories = get_categories()
    category_counts = {}
    for t in TEMPLATES.values():
        category_counts[t.category] = category_counts.get(t.category, 0) + 1
    
    return {
        "categories": [
            {"name": cat, "count": category_counts[cat]}
            for cat in categories
        ],
        "total": len(categories)
    }


@router.get("/templates/{template_id}")
async def get_agent_template(template_id: str):
    """
    Get details of a specific template.
    
    Example:
    ```
    GET /api/v1/agents/templates/researcher
    ```
    """
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    
    return {
        "id": template_id,
        **template.to_dict(),
        "full_system_prompt": template.system_prompt
    }


@router.post("/templates/{template_id}/run")
async def run_template_agent(template_id: str, request: TemplateRunRequest):
    """
    Run an agent using a specific template.
    
    Templates provide pre-configured agents with optimized prompts,
    tools, and settings for specific use cases.
    
    Example:
    ```
    POST /api/v1/agents/templates/researcher/run
    {
        "task": "Research the latest AI trends in 2025",
        "template_id": "researcher"
    }
    ```
    """
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    
    # Handle streaming
    if request.stream:
        return StreamingResponse(
            stream_template_agent(template_id, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    
    try:
        # Create agent from template
        agent_instance = await create_agent_from_template(
            template_id=template_id,
            llm_router=llm_router,
            tool_registry=tool_registry,
            model=request.model,
            temperature=request.temperature
        )
        
        # Run based on pattern
        if template.pattern == AgentPattern.PLAN_EXECUTE:
            result = await agent_instance.run(task=request.task)
        elif template.pattern == AgentPattern.MULTI_AGENT:
            # Collect all results from multi-agent run
            results = []
            async for event in agent_instance.run_hierarchical(task=request.task):
                results.append(event)
            result = {
                "events": results,
                "final": results[-1] if results else None
            }
        else:
            # Simple agent
            result = await agent_instance.run(request.task)
        
        return {
            "template": template_id,
            "template_name": template.name,
            "task": request.task,
            "result": result,
            "pattern": template.pattern.value
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


async def stream_template_agent(template_id: str, request: TemplateRunRequest):
    """Stream template agent execution."""
    template = get_template(template_id)
    
    try:
        agent_instance = await create_agent_from_template(
            template_id=template_id,
            llm_router=llm_router,
            tool_registry=tool_registry,
            model=request.model,
            temperature=request.temperature
        )
        
        # Yield template info
        yield f"data: {json.dumps({'type': 'template', 'id': template_id, 'name': template.name})}\n\n"
        
        if template.pattern == AgentPattern.PLAN_EXECUTE:
            async for event in agent_instance.stream(task=request.task):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0)
        elif template.pattern == AgentPattern.MULTI_AGENT:
            async for event in agent_instance.run_hierarchical(task=request.task):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0)
        else:
            async for chunk in agent_instance.stream(request.task):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0)
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.get("/templates/{template_id}/examples")
async def get_template_examples(template_id: str):
    """
    Get example prompts for a template.
    
    These examples show what kinds of tasks the template is best suited for.
    """
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    
    return {
        "template": template_id,
        "name": template.name,
        "examples": template.example_prompts,
        "category": template.category,
        "tags": template.tags
    }

