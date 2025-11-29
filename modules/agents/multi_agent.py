"""
Multi-Agent System - Agents that collaborate to solve complex tasks.

Patterns:
- Sequential: Chain of agents, each building on the previous
- Parallel: Multiple agents work simultaneously, results combined
- Debate: Agents discuss and reach consensus
- Hierarchical: Coordinator delegates to specialist agents

Agent Roles:
- Coordinator: Orchestrates other agents, breaks down tasks
- Researcher: Web search, fact gathering, information retrieval
- Coder: Code generation, debugging, technical implementation
- Analyst: Data analysis, reasoning, critical thinking
- Writer: Content creation, summarization, communication
- Critic: Reviews and improves other agents' work
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import json


class AgentRole(str, Enum):
    COORDINATOR = "coordinator"
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYST = "analyst"
    WRITER = "writer"
    CRITIC = "critic"


class CollaborationPattern(str, Enum):
    SEQUENTIAL = "sequential"      # A -> B -> C
    PARALLEL = "parallel"          # A, B, C simultaneously
    DEBATE = "debate"              # Agents discuss
    HIERARCHICAL = "hierarchical"  # Coordinator -> Specialists


@dataclass
class AgentMessage:
    """Message between agents."""
    from_agent: str
    to_agent: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class AgentState:
    """Current state of an agent."""
    role: AgentRole
    name: str
    status: str = "idle"  # idle, thinking, responding, waiting
    current_task: Optional[str] = None
    messages: List[AgentMessage] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


AGENT_SYSTEM_PROMPTS = {
    AgentRole.COORDINATOR: """You are the Coordinator agent. Your role is to:
1. Analyze complex tasks and break them into subtasks
2. Assign subtasks to specialist agents based on their expertise
3. Synthesize results from all agents into a cohesive response
4. Ensure the team works efficiently together

When given a task, output a JSON plan:
{
    "subtasks": [
        {"agent": "researcher", "task": "..."},
        {"agent": "coder", "task": "..."}
    ]
}""",

    AgentRole.RESEARCHER: """You are the Researcher agent. Your expertise:
- Finding accurate, up-to-date information
- Fact-checking and verification
- Gathering relevant data from multiple sources
- Summarizing research findings

Be thorough and cite your reasoning. Focus on accuracy over speed.""",

    AgentRole.CODER: """You are the Coder agent. Your expertise:
- Writing clean, efficient code
- Debugging and fixing issues
- Explaining technical concepts
- Implementing algorithms and solutions

Always provide working code with explanations. Include error handling.""",

    AgentRole.ANALYST: """You are the Analyst agent. Your expertise:
- Critical thinking and reasoning
- Data analysis and interpretation
- Identifying patterns and insights
- Making logical conclusions

Be analytical and data-driven. Support conclusions with evidence.""",

    AgentRole.WRITER: """You are the Writer agent. Your expertise:
- Clear, engaging communication
- Summarizing complex topics
- Creating well-structured content
- Adapting tone for different audiences

Focus on clarity and readability. Make content accessible.""",

    AgentRole.CRITIC: """You are the Critic agent. Your expertise:
- Reviewing and improving work
- Finding errors and inconsistencies
- Suggesting improvements
- Quality assurance

Be constructive but thorough. Identify both strengths and weaknesses."""
}


class MultiAgentEngine:
    """
    Orchestrates multiple AI agents working together.
    """
    
    def __init__(self):
        self.llm_router = None
        self.agents: Dict[str, AgentState] = {}
        self.conversation_history: List[AgentMessage] = []
        self.tools = None
        
    def set_llm_router(self, router):
        """Set the LLM router for agent communication."""
        self.llm_router = router
        
    def set_tools(self, tools):
        """Set tools available to agents."""
        self.tools = tools
    
    def _create_agent(self, role: AgentRole, name: Optional[str] = None) -> AgentState:
        """Create an agent with a specific role."""
        agent_name = name or f"{role.value}_{len(self.agents)}"
        agent = AgentState(role=role, name=agent_name)
        self.agents[agent_name] = agent
        return agent
    
    async def _agent_think(
        self,
        agent: AgentState,
        task: str,
        context: List[str] = None,
        model: str = "gpt-4o-mini"
    ) -> str:
        """Have an agent process a task."""
        if not self.llm_router:
            raise ValueError("LLM router not configured")
        
        agent.status = "thinking"
        agent.current_task = task
        
        # Build messages with system prompt and context
        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPTS[agent.role]}
        ]
        
        # Add context from other agents
        if context:
            context_text = "\n\n".join([f"[Previous Agent Output]\n{c}" for c in context])
            messages.append({
                "role": "user", 
                "content": f"Context from team:\n{context_text}\n\nYour task: {task}"
            })
        else:
            messages.append({"role": "user", "content": task})
        
        # Get response from LLM
        response = await self.llm_router.run(
            model_id=model,
            messages=messages,
            temperature=0.7
        )
        
        result = response.get("content", "")
        agent.outputs.append(result)
        agent.status = "idle"
        
        return result
    
    async def run_sequential(
        self,
        task: str,
        agents: List[AgentRole],
        model: str = "gpt-4o-mini"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run agents sequentially, each building on the previous.
        
        Example: Researcher -> Analyst -> Writer
        """
        context = []
        final_result = ""
        
        yield {
            "type": "start",
            "pattern": "sequential",
            "agents": [a.value for a in agents],
            "task": task
        }
        
        for i, role in enumerate(agents):
            agent = self._create_agent(role)
            
            yield {
                "type": "agent_start",
                "agent": agent.name,
                "role": role.value,
                "step": i + 1,
                "total_steps": len(agents)
            }
            
            # First agent gets the original task
            # Subsequent agents get task + context
            if i == 0:
                agent_task = task
            else:
                agent_task = f"Building on the previous work, {task}"
            
            result = await self._agent_think(agent, agent_task, context, model)
            context.append(f"[{role.value}]: {result}")
            final_result = result
            
            yield {
                "type": "agent_result",
                "agent": agent.name,
                "role": role.value,
                "result": result
            }
        
        yield {
            "type": "complete",
            "final_result": final_result,
            "agents_used": len(agents)
        }
    
    async def run_parallel(
        self,
        task: str,
        agents: List[AgentRole],
        model: str = "gpt-4o-mini"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run agents in parallel, then combine results.
        """
        yield {
            "type": "start",
            "pattern": "parallel",
            "agents": [a.value for a in agents],
            "task": task
        }
        
        # Create all agents
        agent_objects = [self._create_agent(role) for role in agents]
        
        yield {
            "type": "agents_started",
            "count": len(agents),
            "agents": [{"name": a.name, "role": a.role.value} for a in agent_objects]
        }
        
        # Run all agents in parallel
        tasks = [
            self._agent_think(agent, task, model=model)
            for agent in agent_objects
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Yield individual results
        for agent, result in zip(agent_objects, results):
            yield {
                "type": "agent_result",
                "agent": agent.name,
                "role": agent.role.value,
                "result": result
            }
        
        # Synthesize results with a coordinator
        coordinator = self._create_agent(AgentRole.COORDINATOR, "synthesizer")
        
        yield {
            "type": "synthesis_start",
            "agent": coordinator.name
        }
        
        synthesis_task = f"""Synthesize these perspectives on: "{task}"

{chr(10).join([f'[{a.role.value}]: {r}' for a, r in zip(agent_objects, results)])}

Create a unified, comprehensive response that incorporates the best insights from each perspective."""
        
        final_result = await self._agent_think(coordinator, synthesis_task, model=model)
        
        yield {
            "type": "complete",
            "final_result": final_result,
            "individual_results": [
                {"agent": a.name, "role": a.role.value, "result": r}
                for a, r in zip(agent_objects, results)
            ]
        }
    
    async def run_debate(
        self,
        task: str,
        agents: List[AgentRole] = None,
        rounds: int = 2,
        model: str = "gpt-4o-mini"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Agents debate a topic to reach better conclusions.
        """
        if agents is None:
            agents = [AgentRole.ANALYST, AgentRole.CRITIC]
        
        yield {
            "type": "start",
            "pattern": "debate",
            "agents": [a.value for a in agents],
            "rounds": rounds,
            "task": task
        }
        
        agent_objects = [self._create_agent(role) for role in agents]
        debate_history = []
        
        for round_num in range(rounds):
            yield {
                "type": "round_start",
                "round": round_num + 1,
                "total_rounds": rounds
            }
            
            for agent in agent_objects:
                # Build debate context
                if debate_history:
                    debate_task = f"""Topic: {task}

Previous arguments:
{chr(10).join(debate_history)}

Respond to the previous arguments. You may agree, disagree, or add new perspectives. Be specific and constructive."""
                else:
                    debate_task = f"Topic: {task}\n\nProvide your initial perspective on this topic."
                
                yield {
                    "type": "agent_speaking",
                    "agent": agent.name,
                    "role": agent.role.value,
                    "round": round_num + 1
                }
                
                result = await self._agent_think(agent, debate_task, model=model)
                debate_history.append(f"[{agent.role.value} - Round {round_num + 1}]: {result}")
                
                yield {
                    "type": "agent_argument",
                    "agent": agent.name,
                    "role": agent.role.value,
                    "round": round_num + 1,
                    "argument": result
                }
        
        # Final synthesis
        coordinator = self._create_agent(AgentRole.COORDINATOR, "moderator")
        
        yield {
            "type": "synthesis_start",
            "agent": coordinator.name
        }
        
        synthesis_task = f"""As the moderator of this debate on "{task}", synthesize the key points and conclusions:

{chr(10).join(debate_history)}

Provide:
1. Key points of agreement
2. Key points of disagreement
3. Final balanced conclusion"""
        
        final_result = await self._agent_think(coordinator, synthesis_task, model=model)
        
        yield {
            "type": "complete",
            "final_result": final_result,
            "debate_history": debate_history
        }
    
    async def run_hierarchical(
        self,
        task: str,
        model: str = "gpt-4o-mini"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Coordinator breaks down task and delegates to specialists.
        """
        yield {
            "type": "start",
            "pattern": "hierarchical",
            "task": task
        }
        
        # Coordinator analyzes and creates plan
        coordinator = self._create_agent(AgentRole.COORDINATOR, "coordinator")
        
        yield {
            "type": "planning",
            "agent": coordinator.name
        }
        
        planning_task = f"""Analyze this task and create a delegation plan: "{task}"

Available specialist agents:
- researcher: Finding information, fact-checking
- coder: Writing code, technical implementation
- analyst: Data analysis, reasoning
- writer: Content creation, communication

Output a JSON plan:
{{
    "analysis": "Brief analysis of the task",
    "subtasks": [
        {{"agent": "agent_role", "task": "specific subtask description"}}
    ]
}}"""
        
        plan_result = await self._agent_think(coordinator, planning_task, model=model)
        
        # Parse the plan
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', plan_result)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                plan = {"analysis": plan_result, "subtasks": [
                    {"agent": "analyst", "task": task}
                ]}
        except:
            plan = {"analysis": plan_result, "subtasks": [
                {"agent": "analyst", "task": task}
            ]}
        
        yield {
            "type": "plan_created",
            "plan": plan
        }
        
        # Execute subtasks
        results = []
        for i, subtask in enumerate(plan.get("subtasks", [])):
            agent_role = subtask.get("agent", "analyst")
            agent_task = subtask.get("task", task)
            
            try:
                role = AgentRole(agent_role)
            except:
                role = AgentRole.ANALYST
            
            agent = self._create_agent(role)
            
            yield {
                "type": "subtask_start",
                "agent": agent.name,
                "role": role.value,
                "task": agent_task,
                "step": i + 1,
                "total_steps": len(plan.get("subtasks", []))
            }
            
            result = await self._agent_think(agent, agent_task, model=model)
            results.append({"agent": role.value, "task": agent_task, "result": result})
            
            yield {
                "type": "subtask_complete",
                "agent": agent.name,
                "role": role.value,
                "result": result
            }
        
        # Coordinator synthesizes
        yield {
            "type": "synthesis_start",
            "agent": coordinator.name
        }
        
        synthesis_task = f"""Original task: "{task}"

Results from your team:
{chr(10).join([f'[{r["agent"]}]: {r["result"]}' for r in results])}

Synthesize these results into a comprehensive final answer."""
        
        final_result = await self._agent_think(coordinator, synthesis_task, model=model)
        
        yield {
            "type": "complete",
            "final_result": final_result,
            "plan": plan,
            "subtask_results": results
        }


# Global instance
multi_agent_engine = MultiAgentEngine()

