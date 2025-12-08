"""
Triggers & Webhooks API - Event-driven orchestration.

Enables:
- Webhook endpoints for external events
- Scheduled triggers (cron-like)
- Event-based workflow execution
- Inter-system integration

Part of the Orchestration layer in the AI Agent framework.
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import secrets
import hashlib
import hmac
import json
import sqlite3
import os


router = APIRouter()


# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/triggers.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS webhooks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            secret TEXT,
            workflow_id TEXT,
            action TEXT NOT NULL,
            action_params TEXT,
            enabled INTEGER DEFAULT 1,
            event_count INTEGER DEFAULT 0,
            last_triggered TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trigger_logs (
            id TEXT PRIMARY KEY,
            webhook_id TEXT,
            event_type TEXT,
            payload TEXT,
            result TEXT,
            status TEXT,
            triggered_at TEXT,
            duration_ms REAL,
            FOREIGN KEY (webhook_id) REFERENCES webhooks(id)
        )
    """)
    conn.commit()
    conn.close()


init_db()


class TriggerAction(str, Enum):
    """Actions that can be triggered."""
    RUN_WORKFLOW = "run_workflow"
    RUN_AGENT = "run_agent"
    RAG_QUERY = "rag_query"
    SEND_NOTIFICATION = "send_notification"
    CUSTOM = "custom"


class WebhookCreate(BaseModel):
    """Create a new webhook."""
    name: str
    description: Optional[str] = None
    action: TriggerAction
    action_params: Optional[Dict[str, Any]] = None
    workflow_id: Optional[str] = None
    generate_secret: bool = True


class WebhookUpdate(BaseModel):
    """Update a webhook."""
    name: Optional[str] = None
    description: Optional[str] = None
    action: Optional[TriggerAction] = None
    action_params: Optional[Dict[str, Any]] = None
    workflow_id: Optional[str] = None
    enabled: Optional[bool] = None


class ScheduledTrigger(BaseModel):
    """Scheduled trigger definition."""
    name: str
    cron_expression: str  # e.g., "0 */6 * * *" for every 6 hours
    action: TriggerAction
    action_params: Optional[Dict[str, Any]] = None
    enabled: bool = True


# ============================================
# Webhook Management
# ============================================

@router.get("/webhooks")
async def list_webhooks():
    """
    List all configured webhooks.
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT id, name, description, workflow_id, action, enabled, 
               event_count, last_triggered, created_at 
        FROM webhooks ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    
    webhooks = [
        {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "endpoint": f"/api/v1/triggers/webhook/{row['id']}",
            "workflow_id": row["workflow_id"],
            "action": row["action"],
            "enabled": bool(row["enabled"]),
            "event_count": row["event_count"],
            "last_triggered": row["last_triggered"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]
    
    return {
        "webhooks": webhooks,
        "total": len(webhooks)
    }


@router.post("/webhooks")
async def create_webhook(webhook: WebhookCreate):
    """
    Create a new webhook endpoint.
    
    Returns webhook ID and endpoint URL.
    
    Example:
    ```
    POST /api/v1/triggers/webhooks
    {
        "name": "GitHub Push Handler",
        "action": "run_workflow",
        "workflow_id": "document_analysis",
        "action_params": {"mode": "incremental"}
    }
    ```
    """
    webhook_id = f"wh_{secrets.token_hex(8)}"
    secret = secrets.token_urlsafe(32) if webhook.generate_secret else None
    now = datetime.now().isoformat()
    
    conn = get_db()
    conn.execute("""
        INSERT INTO webhooks 
        (id, name, description, secret, workflow_id, action, action_params, enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        webhook_id,
        webhook.name,
        webhook.description,
        secret,
        webhook.workflow_id,
        webhook.action.value,
        json.dumps(webhook.action_params) if webhook.action_params else None,
        1,
        now,
        now
    ))
    conn.commit()
    conn.close()
    
    return {
        "id": webhook_id,
        "name": webhook.name,
        "endpoint": f"/api/v1/triggers/webhook/{webhook_id}",
        "secret": secret,
        "message": "Webhook created. Use the secret to sign requests."
    }


@router.get("/webhooks/{webhook_id}")
async def get_webhook(webhook_id: str):
    """Get webhook details."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM webhooks WHERE id = ?",
        (webhook_id,)
    ).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "endpoint": f"/api/v1/triggers/webhook/{row['id']}",
        "workflow_id": row["workflow_id"],
        "action": row["action"],
        "action_params": json.loads(row["action_params"]) if row["action_params"] else None,
        "enabled": bool(row["enabled"]),
        "event_count": row["event_count"],
        "last_triggered": row["last_triggered"],
        "created_at": row["created_at"],
        "has_secret": bool(row["secret"])
    }


@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, update: WebhookUpdate):
    """Update a webhook."""
    conn = get_db()
    
    row = conn.execute(
        "SELECT id FROM webhooks WHERE id = ?",
        (webhook_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    updates = ["updated_at = ?"]
    params = [datetime.now().isoformat()]
    
    if update.name is not None:
        updates.append("name = ?")
        params.append(update.name)
    if update.description is not None:
        updates.append("description = ?")
        params.append(update.description)
    if update.action is not None:
        updates.append("action = ?")
        params.append(update.action.value)
    if update.action_params is not None:
        updates.append("action_params = ?")
        params.append(json.dumps(update.action_params))
    if update.workflow_id is not None:
        updates.append("workflow_id = ?")
        params.append(update.workflow_id)
    if update.enabled is not None:
        updates.append("enabled = ?")
        params.append(1 if update.enabled else 0)
    
    params.append(webhook_id)
    
    conn.execute(
        f"UPDATE webhooks SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()
    conn.close()
    
    return {"message": "Webhook updated", "id": webhook_id}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook."""
    conn = get_db()
    
    row = conn.execute(
        "SELECT id FROM webhooks WHERE id = ?",
        (webhook_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    conn.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
    conn.execute("DELETE FROM trigger_logs WHERE webhook_id = ?", (webhook_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Webhook deleted"}


@router.post("/webhooks/{webhook_id}/regenerate-secret")
async def regenerate_webhook_secret(webhook_id: str):
    """Regenerate webhook secret."""
    conn = get_db()
    
    row = conn.execute(
        "SELECT id FROM webhooks WHERE id = ?",
        (webhook_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    new_secret = secrets.token_urlsafe(32)
    
    conn.execute(
        "UPDATE webhooks SET secret = ?, updated_at = ? WHERE id = ?",
        (new_secret, datetime.now().isoformat(), webhook_id)
    )
    conn.commit()
    conn.close()
    
    return {
        "message": "Secret regenerated",
        "secret": new_secret
    }


# ============================================
# Webhook Execution Endpoint
# ============================================

@router.post("/webhook/{webhook_id}")
async def trigger_webhook(
    webhook_id: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive and process webhook events.
    
    This is the endpoint external systems call to trigger actions.
    
    Supports:
    - JSON body payloads
    - Optional HMAC signature verification (X-Signature header)
    """
    import time
    start_time = time.time()
    
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM webhooks WHERE id = ?",
        (webhook_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    if not row["enabled"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Webhook is disabled")
    
    # Get payload
    try:
        payload = await request.json()
    except:
        payload = {}
    
    # Verify signature if secret is set
    if row["secret"]:
        signature = request.headers.get("X-Signature")
        if signature:
            body = await request.body()
            expected_sig = hmac.new(
                row["secret"].encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, f"sha256={expected_sig}"):
                conn.close()
                raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Execute the action
    action = row["action"]
    action_params = json.loads(row["action_params"]) if row["action_params"] else {}
    workflow_id = row["workflow_id"]
    
    result = None
    status = "success"
    
    try:
        if action == "run_workflow" and workflow_id:
            from core.orchestrator import orchestrator
            result = await orchestrator.execute(
                workflow_name=workflow_id,
                payload={**payload, **action_params}
            )
            result = result.to_dict() if hasattr(result, 'to_dict') else str(result)
            
        elif action == "run_agent":
            from modules.agents import agent
            task = payload.get("task", action_params.get("task", "Process webhook event"))
            agent_result = await agent.run(task=task, context=json.dumps(payload))
            result = {
                "answer": agent_result.answer,
                "tools_used": agent_result.tools_used
            }
            
        elif action == "rag_query":
            from modules.rag import rag_engine
            query = payload.get("query", action_params.get("query"))
            if query:
                rag_result = await rag_engine.query(query=query)
                result = {
                    "answer": rag_result.answer,
                    "sources_count": len(rag_result.sources)
                }
            else:
                result = {"error": "No query provided"}
                status = "error"
                
        elif action == "send_notification":
            # Would integrate with notification service
            result = {
                "notification": "sent",
                "message": action_params.get("message", "Webhook triggered")
            }
            
        else:
            result = {"received": True, "payload": payload}
            
    except Exception as e:
        result = {"error": str(e)}
        status = "error"
    
    duration_ms = (time.time() - start_time) * 1000
    
    # Log the trigger event
    log_id = f"log_{secrets.token_hex(8)}"
    conn.execute("""
        INSERT INTO trigger_logs 
        (id, webhook_id, event_type, payload, result, status, triggered_at, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id,
        webhook_id,
        action,
        json.dumps(payload)[:5000],
        json.dumps(result)[:5000] if result else None,
        status,
        datetime.now().isoformat(),
        duration_ms
    ))
    
    # Update webhook stats
    conn.execute("""
        UPDATE webhooks 
        SET event_count = event_count + 1, last_triggered = ? 
        WHERE id = ?
    """, (datetime.now().isoformat(), webhook_id))
    
    conn.commit()
    conn.close()
    
    return {
        "webhook_id": webhook_id,
        "status": status,
        "action": action,
        "result": result,
        "duration_ms": duration_ms
    }


# ============================================
# Trigger Logs
# ============================================

@router.get("/webhooks/{webhook_id}/logs")
async def get_webhook_logs(
    webhook_id: str,
    limit: int = 50,
    status: Optional[str] = None
):
    """Get trigger execution logs for a webhook."""
    conn = get_db()
    
    query = "SELECT * FROM trigger_logs WHERE webhook_id = ?"
    params = [webhook_id]
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY triggered_at DESC LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    logs = [
        {
            "id": row["id"],
            "event_type": row["event_type"],
            "status": row["status"],
            "payload": json.loads(row["payload"]) if row["payload"] else None,
            "result": json.loads(row["result"]) if row["result"] else None,
            "triggered_at": row["triggered_at"],
            "duration_ms": row["duration_ms"]
        }
        for row in rows
    ]
    
    return {
        "logs": logs,
        "total": len(logs),
        "webhook_id": webhook_id
    }


# ============================================
# Event Types & Quick Triggers
# ============================================

@router.get("/event-types")
async def list_event_types():
    """List supported event types for documentation."""
    return {
        "actions": [
            {
                "name": "run_workflow",
                "description": "Execute a workflow with the payload",
                "requires": "workflow_id"
            },
            {
                "name": "run_agent",
                "description": "Run an AI agent with the payload as context",
                "requires": "task in payload or action_params"
            },
            {
                "name": "rag_query",
                "description": "Execute a RAG query",
                "requires": "query in payload or action_params"
            },
            {
                "name": "send_notification",
                "description": "Send a notification",
                "requires": "message in action_params"
            },
            {
                "name": "custom",
                "description": "Custom action (logs event only)",
                "requires": None
            }
        ]
    }


@router.post("/quick-trigger")
async def quick_trigger(
    action: TriggerAction,
    payload: Dict[str, Any] = {}
):
    """
    Quick trigger an action without creating a webhook.
    
    For testing and one-off executions.
    
    Example:
    ```
    POST /api/v1/triggers/quick-trigger?action=run_agent
    {"task": "Analyze this data", "data": {...}}
    ```
    """
    import time
    start_time = time.time()
    
    result = None
    status = "success"
    
    try:
        if action == TriggerAction.RUN_AGENT:
            from modules.agents import agent
            task = payload.get("task", "Process this event")
            agent_result = await agent.run(task=task, context=json.dumps(payload))
            result = {
                "answer": agent_result.answer,
                "tools_used": agent_result.tools_used
            }
            
        elif action == TriggerAction.RAG_QUERY:
            from modules.rag import rag_engine
            query = payload.get("query")
            if query:
                rag_result = await rag_engine.query(query=query)
                result = {
                    "answer": rag_result.answer,
                    "sources_count": len(rag_result.sources)
                }
            else:
                raise ValueError("query is required")
                
        else:
            result = {"received": True, "action": action.value}
            
    except Exception as e:
        result = {"error": str(e)}
        status = "error"
    
    return {
        "action": action.value,
        "status": status,
        "result": result,
        "duration_ms": (time.time() - start_time) * 1000
    }


