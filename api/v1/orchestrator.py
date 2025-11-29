from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from core.orchestrator import orchestrator, WorkflowStatus

router = APIRouter()


class WorkflowRequest(BaseModel):
    workflow_name: str
    payload: Dict[str, Any] = {}
    async_mode: Optional[bool] = False


class StepResultModel(BaseModel):
    step_name: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0


class WorkflowResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    steps_completed: int = 0
    total_steps: int = 0
    step_results: List[StepResultModel] = []
    duration_ms: float = 0


class WorkflowDefinition(BaseModel):
    name: str
    description: Optional[str] = ""
    version: Optional[str] = "1.0"
    steps: List[Dict[str, Any]]
    inputs: Optional[Dict[str, Any]] = {}
    outputs: Optional[List[str]] = []
    on_error: Optional[str] = "fail"


@router.post("/execute", response_model=WorkflowResponse)
async def execute_workflow(request: WorkflowRequest):
    """
    Execute a named workflow with the given payload.
    """
    result = await orchestrator.execute(
        workflow_name=request.workflow_name,
        payload=request.payload,
        async_mode=request.async_mode
    )
    
    return WorkflowResponse(
        workflow_id=result.workflow_id,
        workflow_name=result.workflow_name,
        status=result.status.value,
        result=result.result,
        error=result.error,
        steps_completed=result.steps_completed,
        total_steps=result.total_steps,
        step_results=[
            StepResultModel(
                step_name=sr.step_name,
                status=sr.status.value,
                output=sr.output,
                error=sr.error,
                duration_ms=sr.duration_ms
            )
            for sr in result.step_results
        ],
        duration_ms=result.duration_ms
    )


@router.get("/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """
    Get the status of a running workflow.
    """
    result = await orchestrator.get_status(workflow_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    
    return WorkflowResponse(
        workflow_id=result.workflow_id,
        workflow_name=result.workflow_name,
        status=result.status.value,
        result=result.result,
        error=result.error,
        steps_completed=result.steps_completed,
        total_steps=result.total_steps,
        step_results=[
            StepResultModel(
                step_name=sr.step_name,
                status=sr.status.value,
                output=sr.output,
                error=sr.error,
                duration_ms=sr.duration_ms
            )
            for sr in result.step_results
        ],
        duration_ms=result.duration_ms
    )


@router.get("/workflows")
async def list_workflows():
    """
    List all available workflows.
    """
    workflows = orchestrator.list_workflows()
    return {
        "workflows": workflows,
        "count": len(workflows)
    }


@router.post("/register")
async def register_workflow(definition: WorkflowDefinition):
    """
    Register a new workflow definition.
    """
    try:
        orchestrator.register_workflow_from_dict(
            name=definition.name,
            config={
                "description": definition.description,
                "version": definition.version,
                "steps": definition.steps,
                "inputs": definition.inputs,
                "outputs": definition.outputs,
                "on_error": definition.on_error
            }
        )
        
        return {
            "status": "registered",
            "workflow": definition.name,
            "steps": len(definition.steps)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel/{workflow_id}")
async def cancel_workflow(workflow_id: str):
    """
    Cancel a running workflow.
    """
    cancelled = await orchestrator.cancel(workflow_id)
    
    return {
        "workflow_id": workflow_id,
        "cancelled": cancelled,
        "message": "Workflow cancelled" if cancelled else "Workflow not found or already completed"
    }


@router.get("/actions")
async def list_actions():
    """
    List all available workflow actions.
    """
    return {
        "actions": orchestrator.list_actions()
    }


@router.post("/load-yaml")
async def load_workflow_yaml(yaml_path: str):
    """
    Load a workflow from a YAML file.
    """
    try:
        name = orchestrator.load_workflow_from_yaml(yaml_path)
        return {
            "status": "loaded",
            "workflow": name,
            "path": yaml_path
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"YAML file not found: {yaml_path}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/load-directory")
async def load_workflows_from_directory(directory: Optional[str] = None):
    """
    Load all workflow YAML files from a directory.
    """
    try:
        loaded = orchestrator.load_workflows_from_directory(directory)
        return {
            "status": "loaded",
            "workflows": loaded,
            "count": len(loaded)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
