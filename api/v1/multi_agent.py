"""
Multi-Agent API - Collaborative AI agents working together.

Patterns:
- sequential: Agents work in order, each building on previous
- parallel: Agents work simultaneously, results combined
- debate: Agents discuss to reach consensus
- hierarchical: Coordinator delegates to specialists
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
import json

from modules.agents.multi_agent import (
    multi_agent_engine,
    AgentRole,
    CollaborationPattern
)
from core.llm import llm_router


router = APIRouter()

# Wire up the engine
multi_agent_engine.set_llm_router(llm_router)


class AgentRoleEnum(str, Enum):
    coordinator = "coordinator"
    researcher = "researcher"
    coder = "coder"
    analyst = "analyst"
    writer = "writer"
    critic = "critic"


class PatternEnum(str, Enum):
    sequential = "sequential"
    parallel = "parallel"
    debate = "debate"
    hierarchical = "hierarchical"


class MultiAgentRequest(BaseModel):
    """Request for multi-agent collaboration."""
    task: str
    pattern: PatternEnum = PatternEnum.hierarchical
    agents: Optional[List[AgentRoleEnum]] = None
    model: Optional[str] = "gpt-4o-mini"
    debate_rounds: Optional[int] = 2
    stream: bool = True


class TeamPreset(BaseModel):
    """Predefined team configuration."""
    name: str
    description: str
    pattern: str
    agents: List[str]


# Predefined team configurations
TEAM_PRESETS = {
    "research_team": TeamPreset(
        name="Research Team",
        description="Deep research with analysis and writing",
        pattern="sequential",
        agents=["researcher", "analyst", "writer"]
    ),
    "code_review": TeamPreset(
        name="Code Review Team",
        description="Write code, then review and improve",
        pattern="sequential",
        agents=["coder", "critic", "coder"]
    ),
    "brainstorm": TeamPreset(
        name="Brainstorm Team",
        description="Multiple perspectives on a problem",
        pattern="parallel",
        agents=["researcher", "analyst", "coder", "writer"]
    ),
    "debate_team": TeamPreset(
        name="Debate Team",
        description="Analysts debate to find best solution",
        pattern="debate",
        agents=["analyst", "critic"]
    ),
    "full_team": TeamPreset(
        name="Full Team",
        description="Coordinator delegates to all specialists",
        pattern="hierarchical",
        agents=["coordinator", "researcher", "coder", "analyst", "writer"]
    )
}


@router.get("/teams")
async def list_team_presets():
    """
    List available team presets.
    
    Returns predefined team configurations for common use cases.
    """
    return {
        "teams": {k: v.dict() for k, v in TEAM_PRESETS.items()},
        "patterns": [p.value for p in CollaborationPattern],
        "roles": [r.value for r in AgentRole]
    }


@router.get("/roles")
async def list_agent_roles():
    """
    List available agent roles and their capabilities.
    """
    role_descriptions = {
        "coordinator": {
            "name": "Coordinator",
            "icon": "👔",
            "color": "#8b5cf6",
            "capabilities": ["Task breakdown", "Delegation", "Synthesis", "Orchestration"]
        },
        "researcher": {
            "name": "Researcher", 
            "icon": "🔍",
            "color": "#00d4ff",
            "capabilities": ["Information gathering", "Fact-checking", "Source finding", "Summarization"]
        },
        "coder": {
            "name": "Coder",
            "icon": "💻",
            "color": "#10b981",
            "capabilities": ["Code generation", "Debugging", "Technical explanation", "Implementation"]
        },
        "analyst": {
            "name": "Analyst",
            "icon": "📊",
            "color": "#f59e0b",
            "capabilities": ["Data analysis", "Critical thinking", "Pattern recognition", "Reasoning"]
        },
        "writer": {
            "name": "Writer",
            "icon": "✍️",
            "color": "#ec4899",
            "capabilities": ["Content creation", "Summarization", "Communication", "Formatting"]
        },
        "critic": {
            "name": "Critic",
            "icon": "🔎",
            "color": "#ef4444",
            "capabilities": ["Review", "Quality assurance", "Improvement suggestions", "Error detection"]
        }
    }
    
    return {"roles": role_descriptions}


@router.post("/run")
async def run_multi_agent(request: MultiAgentRequest):
    """
    Run a multi-agent collaboration task.
    
    Patterns:
    - **sequential**: Agents work in order (Researcher -> Analyst -> Writer)
    - **parallel**: All agents work simultaneously, results combined
    - **debate**: Agents discuss and refine ideas
    - **hierarchical**: Coordinator breaks down task, delegates to specialists
    
    Example:
    ```
    POST /api/v1/multi-agent/run
    {
        "task": "Create a Python web scraper with error handling",
        "pattern": "sequential",
        "agents": ["researcher", "coder", "critic"],
        "model": "gpt-4o-mini"
    }
    ```
    """
    
    async def generate_stream():
        try:
            # Convert agent roles
            if request.agents:
                agents = [AgentRole(a.value) for a in request.agents]
            else:
                # Default agents based on pattern
                if request.pattern == PatternEnum.debate:
                    agents = [AgentRole.ANALYST, AgentRole.CRITIC]
                elif request.pattern == PatternEnum.parallel:
                    agents = [AgentRole.RESEARCHER, AgentRole.ANALYST, AgentRole.WRITER]
                else:
                    agents = [AgentRole.RESEARCHER, AgentRole.ANALYST, AgentRole.WRITER]
            
            # Select collaboration pattern
            if request.pattern == PatternEnum.sequential:
                generator = multi_agent_engine.run_sequential(
                    task=request.task,
                    agents=agents,
                    model=request.model
                )
            elif request.pattern == PatternEnum.parallel:
                generator = multi_agent_engine.run_parallel(
                    task=request.task,
                    agents=agents,
                    model=request.model
                )
            elif request.pattern == PatternEnum.debate:
                generator = multi_agent_engine.run_debate(
                    task=request.task,
                    agents=agents,
                    rounds=request.debate_rounds,
                    model=request.model
                )
            else:  # hierarchical
                generator = multi_agent_engine.run_hierarchical(
                    task=request.task,
                    model=request.model
                )
            
            async for event in generator:
                yield f"data: {json.dumps(event)}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    if request.stream:
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    else:
        # Non-streaming: collect all events and return final result
        events = []
        final_result = None
        
        if request.agents:
            agents = [AgentRole(a.value) for a in request.agents]
        else:
            agents = [AgentRole.RESEARCHER, AgentRole.ANALYST, AgentRole.WRITER]
        
        if request.pattern == PatternEnum.sequential:
            generator = multi_agent_engine.run_sequential(
                task=request.task, agents=agents, model=request.model
            )
        elif request.pattern == PatternEnum.parallel:
            generator = multi_agent_engine.run_parallel(
                task=request.task, agents=agents, model=request.model
            )
        elif request.pattern == PatternEnum.debate:
            generator = multi_agent_engine.run_debate(
                task=request.task, agents=agents, rounds=request.debate_rounds, model=request.model
            )
        else:
            generator = multi_agent_engine.run_hierarchical(
                task=request.task, model=request.model
            )
        
        async for event in generator:
            events.append(event)
            if event.get("type") == "complete":
                final_result = event.get("final_result")
        
        return {
            "task": request.task,
            "pattern": request.pattern,
            "final_result": final_result,
            "events": events
        }


@router.post("/run/{team_preset}")
async def run_team_preset(team_preset: str, task: str, model: str = "gpt-4o-mini", stream: bool = True):
    """
    Run a predefined team configuration.
    
    Available presets:
    - research_team: Deep research with analysis and writing
    - code_review: Write code, then review and improve
    - brainstorm: Multiple perspectives on a problem
    - debate_team: Analysts debate to find best solution
    - full_team: Coordinator delegates to all specialists
    """
    if team_preset not in TEAM_PRESETS:
        raise HTTPException(status_code=404, detail=f"Team preset '{team_preset}' not found")
    
    preset = TEAM_PRESETS[team_preset]
    
    request = MultiAgentRequest(
        task=task,
        pattern=PatternEnum(preset.pattern),
        agents=[AgentRoleEnum(a) for a in preset.agents if a != "coordinator"],
        model=model,
        stream=stream
    )
    
    return await run_multi_agent(request)

