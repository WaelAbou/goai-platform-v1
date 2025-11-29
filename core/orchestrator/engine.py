"""
Orchestrator Engine - Executes multi-step workflows.
Supports YAML-defined workflows with conditional logic, loops, and parallel execution.
"""

import os
import uuid
import asyncio
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import yaml
import re


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    step_name: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowStep:
    name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    on_error: str = "fail"  # "fail", "continue", "retry"
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 300.0  # 5 minutes default
    depends_on: List[str] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    name: str
    description: str = ""
    version: str = "1.0"
    steps: List[WorkflowStep] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    on_error: str = "fail"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    steps_completed: int = 0
    total_steps: int = 0
    step_results: List[StepResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0


class WorkflowContext:
    """Context object passed between workflow steps"""

    def __init__(self, workflow_id: str, payload: Dict[str, Any]):
        self.workflow_id = workflow_id
        self.payload = payload
        self.variables: Dict[str, Any] = {}
        self.step_outputs: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from context (checks step outputs, then variables, then payload)"""
        if key in self.step_outputs:
            return self.step_outputs[key]
        if key in self.variables:
            return self.variables[key]
        return self.payload.get(key, default)

    def set(self, key: str, value: Any):
        """Set a variable in context"""
        self.variables[key] = value

    def set_step_output(self, step_name: str, output: Any):
        """Store output from a step"""
        self.step_outputs[step_name] = output

    def resolve_template(self, template: str) -> str:
        """Resolve template variables like {{step_name.field}} or {{variable}}"""
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace(match):
            path = match.group(1).strip()
            parts = path.split('.')
            
            # Try to resolve the path
            value = self.get(parts[0])
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return match.group(0)  # Return original if can't resolve
            
            return str(value) if value is not None else ""
        
        return re.sub(pattern, replace, template)


# Action registry type
ActionHandler = Callable[[WorkflowContext, Dict[str, Any]], Awaitable[Any]]


class Orchestrator:
    """
    Orchestrates multi-step workflows with LLM and tool integration.
    """

    def __init__(self):
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.running_workflows: Dict[str, WorkflowResult] = {}
        self.action_handlers: Dict[str, ActionHandler] = {}
        self.workflow_dir = Path("workflows")
        
        # Register built-in actions
        self._register_builtin_actions()

    def _register_builtin_actions(self):
        """Register built-in action handlers"""
        
        @self.action("log")
        async def log_action(ctx: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
            message = ctx.resolve_template(params.get("message", ""))
            level = params.get("level", "info")
            print(f"[{level.upper()}] {message}")
            return {"logged": True, "message": message}

        @self.action("set_variable")
        async def set_variable_action(ctx: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
            name = params.get("name")
            value = params.get("value")
            if name:
                # Resolve template if value is a string
                if isinstance(value, str):
                    value = ctx.resolve_template(value)
                ctx.set(name, value)
            return {"name": name, "value": value}

        @self.action("condition")
        async def condition_action(ctx: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
            condition = params.get("condition", "")
            then_value = params.get("then")
            else_value = params.get("else")
            
            # Simple condition evaluation
            result = self._evaluate_condition(condition, ctx)
            return {"result": then_value if result else else_value, "condition_met": result}

        @self.action("http_request")
        async def http_request_action(ctx: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
            import httpx
            
            url = ctx.resolve_template(params.get("url", ""))
            method = params.get("method", "GET").upper()
            headers = params.get("headers", {})
            body = params.get("body")
            
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, headers=headers, json=body)
                return {
                    "status_code": response.status_code,
                    "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                }

        @self.action("parallel")
        async def parallel_action(ctx: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
            """Execute multiple actions in parallel"""
            actions = params.get("actions", [])
            results = await asyncio.gather(*[
                self._execute_action(ctx, action["action"], action.get("params", {}))
                for action in actions
            ], return_exceptions=True)
            return {"results": results}

        @self.action("loop")
        async def loop_action(ctx: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
            """Execute an action for each item in a list"""
            items = params.get("items", [])
            if isinstance(items, str):
                items = ctx.get(items, [])
            
            action = params.get("action")
            action_params = params.get("params", {})
            
            results = []
            for i, item in enumerate(items):
                ctx.set("_item", item)
                ctx.set("_index", i)
                result = await self._execute_action(ctx, action, action_params)
                results.append(result)
            
            return {"results": results, "count": len(results)}

        @self.action("llm_complete")
        async def llm_complete_action(ctx: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
            """Call LLM using the LLM Router"""
            from core.llm import llm_router
            
            model = params.get("model", "gpt-4o-mini")
            messages = params.get("messages", [])
            temperature = params.get("temperature", 0.7)
            
            # Resolve templates in messages
            resolved_messages = []
            for msg in messages:
                resolved_messages.append({
                    "role": msg["role"],
                    "content": ctx.resolve_template(msg["content"])
                })
            
            result = await llm_router.run(model, resolved_messages, temperature=temperature)
            return result

        @self.action("vector_search")
        async def vector_search_action(ctx: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
            """Search vector store"""
            from core.vector import vector_retriever
            
            query = ctx.resolve_template(params.get("query", ""))
            top_k = params.get("top_k", 5)
            
            results = await vector_retriever.search(query, top_k=top_k)
            return {
                "results": [
                    {"id": r.id, "content": r.content, "score": r.score, "metadata": r.metadata}
                    for r in results
                ]
            }

    def action(self, name: str):
        """Decorator to register an action handler"""
        def decorator(func: ActionHandler):
            self.action_handlers[name] = func
            return func
        return decorator

    def register_action(self, name: str, handler: ActionHandler):
        """Register an action handler"""
        self.action_handlers[name] = handler

    def _evaluate_condition(self, condition: str, ctx: WorkflowContext) -> bool:
        """Evaluate a simple condition expression"""
        if not condition:
            return True
        
        # Resolve any templates in the condition
        resolved = ctx.resolve_template(condition)
        
        # Simple evaluations
        if resolved.lower() in ("true", "yes", "1"):
            return True
        if resolved.lower() in ("false", "no", "0", ""):
            return False
        
        # Try to evaluate as Python expression (safely)
        try:
            # Create a safe namespace with context variables
            namespace = {
                **ctx.payload,
                **ctx.variables,
                **ctx.step_outputs
            }
            return bool(eval(resolved, {"__builtins__": {}}, namespace))
        except Exception:
            return False

    async def _execute_action(
        self,
        ctx: WorkflowContext,
        action: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute a single action"""
        handler = self.action_handlers.get(action)
        if handler is None:
            raise ValueError(f"Unknown action: {action}")
        
        # Resolve template strings in params
        resolved_params = {}
        for key, value in params.items():
            if isinstance(value, str):
                resolved_params[key] = ctx.resolve_template(value)
            else:
                resolved_params[key] = value
        
        return await handler(ctx, resolved_params)

    async def _execute_step(
        self,
        step: WorkflowStep,
        ctx: WorkflowContext
    ) -> StepResult:
        """Execute a single workflow step"""
        started_at = datetime.now()
        
        # Check condition
        if step.condition and not self._evaluate_condition(step.condition, ctx):
            return StepResult(
                step_name=step.name,
                status=StepStatus.SKIPPED,
                started_at=started_at,
                completed_at=datetime.now()
            )
        
        try:
            # Execute with timeout
            output = await asyncio.wait_for(
                self._execute_action(ctx, step.action, step.params),
                timeout=step.timeout
            )
            
            # Store output in context
            ctx.set_step_output(step.name, output)
            
            completed_at = datetime.now()
            return StepResult(
                step_name=step.name,
                status=StepStatus.COMPLETED,
                output=output,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=(completed_at - started_at).total_seconds() * 1000
            )
        
        except asyncio.TimeoutError:
            return StepResult(
                step_name=step.name,
                status=StepStatus.FAILED,
                error="Step timed out",
                started_at=started_at,
                completed_at=datetime.now()
            )
        
        except Exception as e:
            # Handle retry logic
            if step.on_error == "retry" and step.retry_count < step.max_retries:
                step.retry_count += 1
                return await self._execute_step(step, ctx)
            
            return StepResult(
                step_name=step.name,
                status=StepStatus.FAILED,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now()
            )

    def register_workflow(self, name: str, definition: WorkflowDefinition):
        """Register a workflow definition"""
        self.workflows[name] = definition

    def register_workflow_from_dict(self, name: str, config: Dict[str, Any]):
        """Register a workflow from a dictionary configuration"""
        steps = []
        for step_config in config.get("steps", []):
            steps.append(WorkflowStep(
                name=step_config["name"],
                action=step_config["action"],
                params=step_config.get("params", {}),
                condition=step_config.get("condition"),
                on_error=step_config.get("on_error", "fail"),
                max_retries=step_config.get("max_retries", 3),
                timeout=step_config.get("timeout", 300.0),
                depends_on=step_config.get("depends_on", [])
            ))
        
        definition = WorkflowDefinition(
            name=name,
            description=config.get("description", ""),
            version=config.get("version", "1.0"),
            steps=steps,
            inputs=config.get("inputs", {}),
            outputs=config.get("outputs", []),
            on_error=config.get("on_error", "fail"),
            metadata=config.get("metadata", {})
        )
        
        self.workflows[name] = definition

    def load_workflow_from_yaml(self, yaml_path: str) -> str:
        """Load workflow definition from YAML file"""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {yaml_path}")
        
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        
        name = config.get("name", path.stem)
        self.register_workflow_from_dict(name, config)
        return name

    def load_workflows_from_directory(self, directory: Optional[str] = None):
        """Load all workflow YAML files from a directory"""
        dir_path = Path(directory) if directory else self.workflow_dir
        if not dir_path.exists():
            return []
        
        loaded = []
        for yaml_file in dir_path.glob("*.yaml"):
            try:
                name = self.load_workflow_from_yaml(str(yaml_file))
                loaded.append(name)
            except Exception as e:
                print(f"Failed to load workflow {yaml_file}: {e}")
        
        for yml_file in dir_path.glob("*.yml"):
            try:
                name = self.load_workflow_from_yaml(str(yml_file))
                loaded.append(name)
            except Exception as e:
                print(f"Failed to load workflow {yml_file}: {e}")
        
        return loaded

    async def execute(
        self,
        workflow_name: str,
        payload: Dict[str, Any],
        async_mode: bool = False
    ) -> WorkflowResult:
        """
        Execute a named workflow with the given payload.
        
        Args:
            workflow_name: Name of the registered workflow
            payload: Input data for the workflow
            async_mode: If True, return immediately with workflow ID
            
        Returns:
            WorkflowResult with execution status and output
        """
        workflow_id = str(uuid.uuid4())
        started_at = datetime.now()
        
        # Get workflow definition
        definition = self.workflows.get(workflow_name)
        if definition is None:
            return WorkflowResult(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                status=WorkflowStatus.FAILED,
                error=f"Workflow '{workflow_name}' not found",
                started_at=started_at,
                completed_at=datetime.now()
            )
        
        # Create initial result
        result = WorkflowResult(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            status=WorkflowStatus.RUNNING,
            total_steps=len(definition.steps),
            started_at=started_at
        )
        self.running_workflows[workflow_id] = result
        
        # If async mode, return immediately
        if async_mode:
            asyncio.create_task(self._run_workflow(workflow_id, definition, payload))
            return result
        
        # Run synchronously
        return await self._run_workflow(workflow_id, definition, payload)

    async def _run_workflow(
        self,
        workflow_id: str,
        definition: WorkflowDefinition,
        payload: Dict[str, Any]
    ) -> WorkflowResult:
        """Internal method to run a workflow"""
        result = self.running_workflows.get(workflow_id)
        if result is None:
            result = WorkflowResult(
                workflow_id=workflow_id,
                workflow_name=definition.name,
                status=WorkflowStatus.RUNNING,
                total_steps=len(definition.steps),
                started_at=datetime.now()
            )
            self.running_workflows[workflow_id] = result
        
        # Create context
        ctx = WorkflowContext(workflow_id, payload)
        
        try:
            # Execute steps in order
            for step in definition.steps:
                # Check if workflow was cancelled
                if result.status == WorkflowStatus.CANCELLED:
                    break
                
                # Check dependencies (simple implementation)
                # In a full implementation, this would handle parallel execution
                
                step_result = await self._execute_step(step, ctx)
                result.step_results.append(step_result)
                
                if step_result.status == StepStatus.COMPLETED:
                    result.steps_completed += 1
                elif step_result.status == StepStatus.FAILED:
                    if step.on_error == "fail" or definition.on_error == "fail":
                        result.status = WorkflowStatus.FAILED
                        result.error = step_result.error
                        break
            
            # Set final status
            if result.status == WorkflowStatus.RUNNING:
                result.status = WorkflowStatus.COMPLETED
            
            # Collect outputs
            if definition.outputs:
                result.result = {
                    key: ctx.get(key) for key in definition.outputs
                }
            else:
                result.result = {
                    "variables": ctx.variables,
                    "step_outputs": ctx.step_outputs
                }
        
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        
        finally:
            result.completed_at = datetime.now()
            result.duration_ms = (result.completed_at - result.started_at).total_seconds() * 1000
        
        return result

    async def get_status(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Get the status of a running workflow"""
        return self.running_workflows.get(workflow_id)

    async def cancel(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        result = self.running_workflows.get(workflow_id)
        if result and result.status == WorkflowStatus.RUNNING:
            result.status = WorkflowStatus.CANCELLED
            return True
        return False

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all registered workflows"""
        return [
            {
                "name": name,
                "description": defn.description,
                "version": defn.version,
                "steps": len(defn.steps)
            }
            for name, defn in self.workflows.items()
        ]

    def list_actions(self) -> List[str]:
        """List all registered actions"""
        return list(self.action_handlers.keys())


# Singleton instance
orchestrator = Orchestrator()
