"""
Plan-and-Execute Agent Pattern

A two-phase agent that:
1. PLAN: Creates a detailed step-by-step plan for complex tasks
2. EXECUTE: Executes each step, using tools as needed
3. REPLAN: Revises the plan based on intermediate results

This pattern is ideal for complex, multi-step tasks that require
careful planning and iterative refinement.
"""

import json
import re
import time
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .tools import tool_registry
from core.llm import llm_router


class PlanStatus(Enum):
    """Status of plan execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REPLANNED = "replanned"


@dataclass
class PlanStep:
    """A single step in the execution plan."""
    step_number: int
    description: str
    tools_needed: List[str] = field(default_factory=list)
    depends_on: List[int] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ExecutionPlan:
    """Complete execution plan for a task."""
    task: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    status: PlanStatus = PlanStatus.PENDING
    revision: int = 0
    final_result: Optional[str] = None


class PlanAndExecuteAgent:
    """
    Plan-and-Execute Agent Implementation.
    
    Flow:
    1. Analyze task and create a detailed plan
    2. Execute each step sequentially
    3. Use tools as needed during execution
    4. Optionally replan if steps fail or new information emerges
    5. Synthesize final result
    """
    
    PLANNER_PROMPT = """You are a strategic planner. Your job is to create detailed, actionable plans.

Given a task, create a step-by-step plan to accomplish it.

Available Tools:
{tools}

IMPORTANT:
- Break complex tasks into clear, atomic steps
- Each step should be independently verifiable
- Identify which tools are needed for each step
- Consider dependencies between steps
- Be specific about what each step should accomplish

Output your plan as JSON:
{{
    "goal": "The ultimate goal we're trying to achieve",
    "steps": [
        {{
            "step_number": 1,
            "description": "Clear description of what this step does",
            "tools_needed": ["tool1", "tool2"],
            "depends_on": []
        }},
        {{
            "step_number": 2,
            "description": "Next step description",
            "tools_needed": ["tool3"],
            "depends_on": [1]
        }}
    ]
}}

Task: {task}

Create a detailed plan:"""

    EXECUTOR_PROMPT = """You are executing step {step_number} of a plan.

Overall Goal: {goal}

Current Step: {step_description}

Previous Steps Results:
{previous_results}

Available Tools:
{tools}

Execute this step. If you need to use a tool, respond with:
```tool
{{"tool": "tool_name", "arguments": {{"arg": "value"}}}}
```

After using tools (or if no tools needed), provide the step result.

Execute step {step_number}:"""

    REPLANNER_PROMPT = """You are replanning a task based on execution results.

Original Task: {task}
Original Goal: {goal}

Completed Steps:
{completed_steps}

Failed Step:
Step {failed_step}: {failed_description}
Error: {error}

Based on what we learned, create a revised plan to complete the remaining work.
Consider what went wrong and how to address it.

Output revised plan as JSON (same format as before):"""

    SYNTHESIZER_PROMPT = """You have completed all steps of a plan. Synthesize the final result.

Task: {task}
Goal: {goal}

Executed Steps:
{all_steps}

Based on all the step results, provide a comprehensive final answer to the original task."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_replans: int = 2,
        max_tool_iterations: int = 3,
        temperature: float = 0.7
    ):
        self.model = model
        self.max_replans = max_replans
        self.max_tool_iterations = max_tool_iterations
        self.temperature = temperature
        self.tools = tool_registry
    
    def _get_tools_description(self) -> str:
        """Get formatted tools description."""
        tools_desc = []
        for tool in self.tools.list_tools():
            params = ", ".join([
                f"{p['name']}: {p['type']}"
                for p in tool['parameters']
            ])
            tools_desc.append(f"- {tool['name']}({params}): {tool['description']}")
        return "\n".join(tools_desc)
    
    def _parse_plan(self, response: str) -> Optional[Dict]:
        """Parse plan JSON from LLM response."""
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        return None
    
    def _extract_tool_calls(self, content: str) -> List[Dict]:
        """Extract tool calls from response."""
        tool_calls = []
        pattern = r'```tool\s*\n?(.*?)\n?```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads(match.strip())
                if "tool" in tool_call:
                    tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    async def _create_plan(self, task: str) -> ExecutionPlan:
        """Create an execution plan for the task."""
        prompt = self.PLANNER_PROMPT.format(
            tools=self._get_tools_description(),
            task=task
        )
        
        response = await llm_router.run(
            model_id=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )
        
        content = response.get("content", "")
        plan_data = self._parse_plan(content)
        
        if not plan_data:
            # Create a simple single-step plan as fallback
            return ExecutionPlan(
                task=task,
                goal=task,
                steps=[PlanStep(
                    step_number=1,
                    description=f"Complete the task: {task}",
                    tools_needed=[]
                )]
            )
        
        steps = []
        for step_data in plan_data.get("steps", []):
            steps.append(PlanStep(
                step_number=step_data.get("step_number", len(steps) + 1),
                description=step_data.get("description", ""),
                tools_needed=step_data.get("tools_needed", []),
                depends_on=step_data.get("depends_on", [])
            ))
        
        return ExecutionPlan(
            task=task,
            goal=plan_data.get("goal", task),
            steps=steps
        )
    
    async def _execute_step(
        self,
        plan: ExecutionPlan,
        step: PlanStep,
        previous_results: Dict[int, str]
    ) -> str:
        """Execute a single step of the plan."""
        # Format previous results
        prev_results_str = "\n".join([
            f"Step {num}: {result}"
            for num, result in previous_results.items()
        ]) or "None yet"
        
        prompt = self.EXECUTOR_PROMPT.format(
            step_number=step.step_number,
            goal=plan.goal,
            step_description=step.description,
            previous_results=prev_results_str,
            tools=self._get_tools_description()
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        # Execute with potential tool use
        for _ in range(self.max_tool_iterations):
            response = await llm_router.run(
                model_id=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            content = response.get("content", "")
            tool_calls = self._extract_tool_calls(content)
            
            if tool_calls:
                # Execute tools
                tool_results = []
                for call in tool_calls:
                    tool_name = call.get("tool")
                    arguments = call.get("arguments", {})
                    result = await self.tools.execute(tool_name, **arguments)
                    tool_results.append({
                        "tool": tool_name,
                        "result": result
                    })
                
                # Add to conversation and continue
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"Tool results:\n{json.dumps(tool_results, indent=2)}\n\nContinue with the step or provide the result."
                })
            else:
                # No more tools needed, return the result
                return content
        
        return content
    
    async def _replan(
        self,
        plan: ExecutionPlan,
        failed_step: PlanStep,
        error: str
    ) -> ExecutionPlan:
        """Create a new plan after a failure."""
        completed_steps = "\n".join([
            f"Step {s.step_number}: {s.description}\nResult: {s.result}"
            for s in plan.steps if s.status == PlanStatus.COMPLETED
        ]) or "None"
        
        prompt = self.REPLANNER_PROMPT.format(
            task=plan.task,
            goal=plan.goal,
            completed_steps=completed_steps,
            failed_step=failed_step.step_number,
            failed_description=failed_step.description,
            error=error
        )
        
        response = await llm_router.run(
            model_id=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )
        
        content = response.get("content", "")
        plan_data = self._parse_plan(content)
        
        if plan_data:
            new_steps = []
            for step_data in plan_data.get("steps", []):
                new_steps.append(PlanStep(
                    step_number=step_data.get("step_number", len(new_steps) + 1),
                    description=step_data.get("description", ""),
                    tools_needed=step_data.get("tools_needed", []),
                    depends_on=step_data.get("depends_on", [])
                ))
            
            return ExecutionPlan(
                task=plan.task,
                goal=plan_data.get("goal", plan.goal),
                steps=new_steps,
                revision=plan.revision + 1
            )
        
        return plan
    
    async def _synthesize_result(self, plan: ExecutionPlan) -> str:
        """Synthesize final result from all step results."""
        all_steps = "\n\n".join([
            f"Step {s.step_number}: {s.description}\nResult: {s.result}"
            for s in plan.steps if s.result
        ])
        
        prompt = self.SYNTHESIZER_PROMPT.format(
            task=plan.task,
            goal=plan.goal,
            all_steps=all_steps
        )
        
        response = await llm_router.run(
            model_id=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )
        
        return response.get("content", "")
    
    async def run(self, task: str) -> Dict[str, Any]:
        """
        Execute the plan-and-execute pattern.
        
        Returns:
            Dict with plan, steps, and final result
        """
        start_time = time.time()
        replan_count = 0
        
        # Phase 1: Create plan
        plan = await self._create_plan(task)
        plan.status = PlanStatus.IN_PROGRESS
        
        # Phase 2: Execute steps
        previous_results: Dict[int, str] = {}
        
        for step in plan.steps:
            step.started_at = datetime.now()
            step.status = PlanStatus.IN_PROGRESS
            
            try:
                result = await self._execute_step(plan, step, previous_results)
                step.result = result
                step.status = PlanStatus.COMPLETED
                step.completed_at = datetime.now()
                previous_results[step.step_number] = result
                
            except Exception as e:
                step.error = str(e)
                step.status = PlanStatus.FAILED
                step.completed_at = datetime.now()
                
                # Try replanning
                if replan_count < self.max_replans:
                    replan_count += 1
                    plan = await self._replan(plan, step, str(e))
                    plan.status = PlanStatus.REPLANNED
                    # Reset and continue with new plan
                    previous_results = {}
                    for s in plan.steps:
                        if s.status == PlanStatus.COMPLETED:
                            previous_results[s.step_number] = s.result or ""
                else:
                    plan.status = PlanStatus.FAILED
                    break
        
        # Phase 3: Synthesize result
        if plan.status != PlanStatus.FAILED:
            plan.final_result = await self._synthesize_result(plan)
            plan.status = PlanStatus.COMPLETED
        
        return {
            "task": plan.task,
            "goal": plan.goal,
            "status": plan.status.value,
            "revision": plan.revision,
            "steps": [
                {
                    "step_number": s.step_number,
                    "description": s.description,
                    "tools_needed": s.tools_needed,
                    "status": s.status.value,
                    "result": s.result,
                    "error": s.error
                }
                for s in plan.steps
            ],
            "final_result": plan.final_result,
            "latency_ms": (time.time() - start_time) * 1000,
            "replans": replan_count
        }
    
    async def stream(self, task: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream the plan-and-execute process.
        
        Yields events for each phase and step.
        """
        start_time = time.time()
        replan_count = 0
        
        # Phase 1: Planning
        yield {
            "type": "phase",
            "phase": "planning",
            "message": "Creating execution plan..."
        }
        
        plan = await self._create_plan(task)
        plan.status = PlanStatus.IN_PROGRESS
        
        yield {
            "type": "plan_created",
            "goal": plan.goal,
            "steps": [
                {
                    "step_number": s.step_number,
                    "description": s.description,
                    "tools_needed": s.tools_needed
                }
                for s in plan.steps
            ],
            "total_steps": len(plan.steps)
        }
        
        # Phase 2: Execution
        yield {
            "type": "phase",
            "phase": "execution",
            "message": "Executing plan..."
        }
        
        previous_results: Dict[int, str] = {}
        
        for i, step in enumerate(plan.steps):
            yield {
                "type": "step_start",
                "step_number": step.step_number,
                "description": step.description,
                "progress": f"{i + 1}/{len(plan.steps)}"
            }
            
            step.started_at = datetime.now()
            step.status = PlanStatus.IN_PROGRESS
            
            try:
                result = await self._execute_step(plan, step, previous_results)
                step.result = result
                step.status = PlanStatus.COMPLETED
                step.completed_at = datetime.now()
                previous_results[step.step_number] = result
                
                yield {
                    "type": "step_complete",
                    "step_number": step.step_number,
                    "result": result
                }
                
            except Exception as e:
                step.error = str(e)
                step.status = PlanStatus.FAILED
                
                yield {
                    "type": "step_failed",
                    "step_number": step.step_number,
                    "error": str(e)
                }
                
                if replan_count < self.max_replans:
                    replan_count += 1
                    
                    yield {
                        "type": "replanning",
                        "reason": str(e),
                        "attempt": replan_count
                    }
                    
                    plan = await self._replan(plan, step, str(e))
                    
                    yield {
                        "type": "plan_revised",
                        "new_steps": [
                            {
                                "step_number": s.step_number,
                                "description": s.description
                            }
                            for s in plan.steps
                        ]
                    }
                else:
                    plan.status = PlanStatus.FAILED
                    yield {
                        "type": "failed",
                        "error": "Max replanning attempts exceeded"
                    }
                    return
        
        # Phase 3: Synthesis
        yield {
            "type": "phase",
            "phase": "synthesis",
            "message": "Synthesizing final result..."
        }
        
        final_result = await self._synthesize_result(plan)
        plan.final_result = final_result
        plan.status = PlanStatus.COMPLETED
        
        yield {
            "type": "complete",
            "final_result": final_result,
            "steps_completed": len([s for s in plan.steps if s.status == PlanStatus.COMPLETED]),
            "replans": replan_count,
            "latency_ms": (time.time() - start_time) * 1000
        }


# Default instance
plan_execute_agent = PlanAndExecuteAgent()

