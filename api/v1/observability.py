"""
Agent Observability API

Provides monitoring, tracing, and analytics endpoints for AI agent operations.

Endpoints:
- GET /dashboard - Complete dashboard data
- GET /traces - List traces with filters
- GET /traces/{id} - Get specific trace with events
- GET /traces/active - Get currently running traces
- GET /stats - Aggregated statistics
- GET /stats/tools - Tool usage statistics
- GET /stats/models - Model usage statistics
- GET /stats/cost - Cost breakdown
- GET /errors - Recent errors
- GET /stream - Real-time event stream (SSE)
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, HTMLResponse
from typing import Optional
from datetime import datetime, timedelta
import json
import asyncio

from modules.agents.observability import (
    agent_observer,
    TraceStatus,
    EventType
)

router = APIRouter()


# ============================================
# Dashboard Endpoints
# ============================================

@router.get("/dashboard")
async def get_dashboard():
    """
    Get comprehensive dashboard data.
    
    Returns:
    - Summary metrics (executions, tokens, cost)
    - Success/error rates
    - Usage by model, template, tool
    - Recent and active traces
    - Hourly statistics
    
    Example:
    ```
    GET /api/v1/observability/dashboard
    ```
    """
    return agent_observer.get_dashboard_data()


@router.get("/dashboard/html")
async def get_dashboard_html():
    """
    Get an HTML dashboard page.
    
    Provides a visual dashboard for monitoring agent operations.
    """
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>GoAI Agent Observability</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --border: #334155;
            --text: #e2e8f0;
            --text-dim: #94a3b8;
            --accent: #22d3ee;
            --success: #4ade80;
            --error: #f87171;
            --warning: #fbbf24;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'SF Pro Display', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 24px; }
        header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
        }
        h1 { 
            font-size: 28px; 
            font-weight: 600;
            background: linear-gradient(135deg, var(--accent), #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status { 
            display: flex; 
            align-items: center; 
            gap: 8px;
            color: var(--success);
        }
        .status::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Summary Cards */
        .summary { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }
        .card-label { 
            font-size: 13px; 
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .card-value { 
            font-size: 32px; 
            font-weight: 700;
        }
        .card-value.accent { color: var(--accent); }
        .card-value.success { color: var(--success); }
        .card-value.error { color: var(--error); }
        .card-change {
            font-size: 12px;
            color: var(--text-dim);
            margin-top: 4px;
        }
        
        /* Grid Layout */
        .grid { 
            display: grid; 
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }
        @media (max-width: 1024px) {
            .grid { grid-template-columns: 1fr; }
        }
        
        /* Section Headers */
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        h2 { 
            font-size: 18px; 
            font-weight: 600;
        }
        
        /* Traces Table */
        .traces-table {
            width: 100%;
            border-collapse: collapse;
        }
        .traces-table th {
            text-align: left;
            padding: 12px;
            font-size: 12px;
            color: var(--text-dim);
            text-transform: uppercase;
            border-bottom: 1px solid var(--border);
        }
        .traces-table td {
            padding: 12px;
            border-bottom: 1px solid var(--border);
        }
        .traces-table tr:hover {
            background: rgba(255,255,255,0.02);
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-badge.completed { background: rgba(74, 222, 128, 0.2); color: var(--success); }
        .status-badge.running { background: rgba(34, 211, 238, 0.2); color: var(--accent); }
        .status-badge.failed { background: rgba(248, 113, 113, 0.2); color: var(--error); }
        
        /* Usage Stats */
        .usage-list {
            list-style: none;
        }
        .usage-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }
        .usage-item:last-child { border-bottom: none; }
        .usage-bar {
            width: 60px;
            height: 4px;
            background: var(--border);
            border-radius: 2px;
            overflow: hidden;
        }
        .usage-bar-fill {
            height: 100%;
            background: var(--accent);
            border-radius: 2px;
        }
        
        /* Chart Container */
        .chart-container {
            height: 200px;
            display: flex;
            align-items: flex-end;
            gap: 4px;
            padding: 16px 0;
        }
        .chart-bar {
            flex: 1;
            background: linear-gradient(to top, var(--accent), rgba(34, 211, 238, 0.3));
            border-radius: 4px 4px 0 0;
            min-height: 4px;
            transition: height 0.3s;
        }
        .chart-bar:hover {
            background: var(--accent);
        }
        
        /* Events Feed */
        .events-feed {
            max-height: 300px;
            overflow-y: auto;
        }
        .event-item {
            display: flex;
            gap: 12px;
            padding: 12px;
            border-bottom: 1px solid var(--border);
        }
        .event-type {
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            background: var(--border);
            white-space: nowrap;
        }
        .event-time {
            font-size: 12px;
            color: var(--text-dim);
        }
        
        /* Refresh Button */
        .btn {
            padding: 8px 16px;
            background: var(--accent);
            color: var(--bg);
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
        }
        .btn:hover { opacity: 0.9; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Agent Observability</h1>
            <div class="status">Live</div>
        </header>
        
        <div class="summary" id="summary">
            <div class="card">
                <div class="card-label">Total Executions</div>
                <div class="card-value accent" id="total-executions">-</div>
                <div class="card-change" id="executions-24h">Last 24h: -</div>
            </div>
            <div class="card">
                <div class="card-label">Active Traces</div>
                <div class="card-value" id="active-traces">-</div>
            </div>
            <div class="card">
                <div class="card-label">Success Rate</div>
                <div class="card-value success" id="success-rate">-</div>
            </div>
            <div class="card">
                <div class="card-label">Total Tokens</div>
                <div class="card-value" id="total-tokens">-</div>
            </div>
            <div class="card">
                <div class="card-label">Estimated Cost</div>
                <div class="card-value accent" id="total-cost">-</div>
            </div>
            <div class="card">
                <div class="card-label">Avg Duration</div>
                <div class="card-value" id="avg-duration">-</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="section-header">
                    <h2>📊 Hourly Activity</h2>
                </div>
                <div class="chart-container" id="hourly-chart"></div>
            </div>
            
            <div class="card">
                <div class="section-header">
                    <h2>🛠️ Tool Usage</h2>
                </div>
                <ul class="usage-list" id="tool-usage"></ul>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 24px;">
            <div class="section-header">
                <h2>📋 Recent Traces</h2>
                <button class="btn" onclick="refresh()">Refresh</button>
            </div>
            <table class="traces-table">
                <thead>
                    <tr>
                        <th>Status</th>
                        <th>Task</th>
                        <th>Model</th>
                        <th>Tokens</th>
                        <th>Duration</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody id="traces-table"></tbody>
            </table>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="section-header">
                    <h2>⚠️ Recent Errors</h2>
                </div>
                <div class="events-feed" id="errors-feed"></div>
            </div>
            
            <div class="card">
                <div class="section-header">
                    <h2>🤖 Model Usage</h2>
                </div>
                <ul class="usage-list" id="model-usage"></ul>
            </div>
        </div>
    </div>
    
    <script>
        async function fetchData() {
            const res = await fetch('/api/v1/observability/dashboard');
            return await res.json();
        }
        
        function formatNumber(n) {
            if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
            if (n >= 1000) return (n/1000).toFixed(1) + 'K';
            return n.toString();
        }
        
        function formatDuration(ms) {
            if (ms >= 60000) return (ms/60000).toFixed(1) + 'm';
            if (ms >= 1000) return (ms/1000).toFixed(1) + 's';
            return Math.round(ms) + 'ms';
        }
        
        async function render() {
            const data = await fetchData();
            
            // Summary
            document.getElementById('total-executions').textContent = formatNumber(data.summary.total_executions);
            document.getElementById('executions-24h').textContent = 'Last 24h: ' + data.summary.traces_last_24h;
            document.getElementById('active-traces').textContent = data.summary.active_traces;
            document.getElementById('success-rate').textContent = data.rates.success_rate_24h + '%';
            document.getElementById('total-tokens').textContent = formatNumber(data.summary.total_tokens);
            document.getElementById('total-cost').textContent = '$' + data.summary.total_cost.toFixed(4);
            document.getElementById('avg-duration').textContent = formatDuration(data.rates.avg_duration_ms);
            
            // Hourly Chart
            const chartContainer = document.getElementById('hourly-chart');
            chartContainer.innerHTML = '';
            const maxExec = Math.max(...data.hourly_stats.map(h => h.executions), 1);
            data.hourly_stats.forEach(h => {
                const bar = document.createElement('div');
                bar.className = 'chart-bar';
                bar.style.height = (h.executions / maxExec * 100) + '%';
                bar.title = h.display + ': ' + h.executions + ' executions';
                chartContainer.appendChild(bar);
            });
            
            // Tool Usage
            const toolList = document.getElementById('tool-usage');
            toolList.innerHTML = '';
            const tools = Object.entries(data.usage.by_tool).sort((a,b) => b[1] - a[1]).slice(0, 5);
            const maxTool = tools[0]?.[1] || 1;
            tools.forEach(([tool, count]) => {
                const li = document.createElement('li');
                li.className = 'usage-item';
                li.innerHTML = `
                    <span>${tool}</span>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div class="usage-bar"><div class="usage-bar-fill" style="width: ${count/maxTool*100}%"></div></div>
                        <span style="color: var(--text-dim); font-size: 13px;">${count}</span>
                    </div>
                `;
                toolList.appendChild(li);
            });
            
            // Recent Traces
            const tbody = document.getElementById('traces-table');
            tbody.innerHTML = '';
            data.recent_traces.slice(0, 10).forEach(t => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><span class="status-badge ${t.status}">${t.status}</span></td>
                    <td>${t.task}</td>
                    <td>${t.model || '-'}</td>
                    <td>${formatNumber(t.metrics.total_tokens)}</td>
                    <td>${formatDuration(t.duration_ms)}</td>
                    <td>$${t.metrics.estimated_cost.toFixed(4)}</td>
                `;
                tbody.appendChild(tr);
            });
            
            // Errors
            const errorsFeed = document.getElementById('errors-feed');
            errorsFeed.innerHTML = '';
            if (data.recent_errors.length === 0) {
                errorsFeed.innerHTML = '<div style="color: var(--text-dim); padding: 20px; text-align: center;">No recent errors ✨</div>';
            } else {
                data.recent_errors.forEach(e => {
                    const div = document.createElement('div');
                    div.className = 'event-item';
                    div.innerHTML = `
                        <span class="event-type" style="background: rgba(248,113,113,0.2); color: var(--error);">ERROR</span>
                        <div style="flex: 1;">
                            <div>${e.error}</div>
                            <div class="event-time">${e.timestamp}</div>
                        </div>
                    `;
                    errorsFeed.appendChild(div);
                });
            }
            
            // Model Usage
            const modelList = document.getElementById('model-usage');
            modelList.innerHTML = '';
            const models = Object.entries(data.usage.by_model).sort((a,b) => b[1] - a[1]);
            const maxModel = models[0]?.[1] || 1;
            models.forEach(([model, count]) => {
                const li = document.createElement('li');
                li.className = 'usage-item';
                li.innerHTML = `
                    <span>${model}</span>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div class="usage-bar"><div class="usage-bar-fill" style="width: ${count/maxModel*100}%"></div></div>
                        <span style="color: var(--text-dim); font-size: 13px;">${count}</span>
                    </div>
                `;
                modelList.appendChild(li);
            });
        }
        
        function refresh() {
            render();
        }
        
        // Initial render and auto-refresh
        render();
        setInterval(render, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)


# ============================================
# Trace Endpoints
# ============================================

@router.get("/traces")
async def list_traces(
    status: Optional[str] = Query(None, description="Filter by status"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    model: Optional[str] = Query(None, description="Filter by model"),
    template: Optional[str] = Query(None, description="Filter by template"),
    hours: int = Query(24, description="Look back hours"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    List agent traces with optional filters.
    
    Example:
    ```
    GET /api/v1/observability/traces?status=completed&limit=20
    ```
    """
    status_filter = TraceStatus(status) if status else None
    since = datetime.now() - timedelta(hours=hours)
    
    traces = agent_observer.list_traces(
        status=status_filter,
        agent_id=agent_id,
        model=model,
        template=template,
        since=since,
        limit=limit
    )
    
    return {
        "traces": [t.to_dict() for t in traces],
        "count": len(traces),
        "filters": {
            "status": status,
            "agent_id": agent_id,
            "model": model,
            "hours": hours
        }
    }


@router.get("/traces/active")
async def get_active_traces():
    """
    Get currently running agent traces.
    
    Example:
    ```
    GET /api/v1/observability/traces/active
    ```
    """
    traces = agent_observer.get_active_traces()
    return {
        "traces": [t.to_dict() for t in traces],
        "count": len(traces)
    }


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, include_events: bool = True):
    """
    Get a specific trace with full details.
    
    Example:
    ```
    GET /api/v1/observability/traces/abc123?include_events=true
    ```
    """
    trace = agent_observer.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    
    if include_events:
        return trace.to_full_dict()
    return trace.to_dict()


# ============================================
# Statistics Endpoints
# ============================================

@router.get("/stats")
async def get_stats():
    """
    Get aggregated statistics.
    """
    dashboard = agent_observer.get_dashboard_data()
    return {
        "summary": dashboard["summary"],
        "rates": dashboard["rates"],
        "hourly_stats": dashboard["hourly_stats"]
    }


@router.get("/stats/tools")
async def get_tool_stats():
    """
    Get tool usage statistics.
    
    Example:
    ```
    GET /api/v1/observability/stats/tools
    ```
    """
    return agent_observer.get_tool_stats()


@router.get("/stats/models")
async def get_model_stats():
    """
    Get model usage statistics.
    
    Example:
    ```
    GET /api/v1/observability/stats/models
    ```
    """
    return agent_observer.get_model_stats()


@router.get("/stats/cost")
async def get_cost_stats():
    """
    Get cost breakdown by model.
    
    Example:
    ```
    GET /api/v1/observability/stats/cost
    ```
    """
    return agent_observer.get_cost_breakdown()


# ============================================
# Error Monitoring
# ============================================

@router.get("/errors")
async def get_recent_errors(limit: int = Query(20, ge=1, le=100)):
    """
    Get recent errors.
    
    Example:
    ```
    GET /api/v1/observability/errors?limit=10
    ```
    """
    errors = agent_observer.get_recent_errors(limit)
    return {
        "errors": errors,
        "count": len(errors)
    }


# ============================================
# Real-time Streaming
# ============================================

@router.get("/stream")
async def stream_events(trace_id: Optional[str] = None):
    """
    Stream events in real-time (Server-Sent Events).
    
    Example:
    ```
    GET /api/v1/observability/stream
    GET /api/v1/observability/stream?trace_id=abc123
    ```
    """
    async def event_generator():
        queue = agent_observer.subscribe()
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    if trace_id and event.get("trace_id") != trace_id:
                        continue
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        finally:
            agent_observer.unsubscribe(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


# ============================================
# Info Endpoint
# ============================================

@router.get("/")
async def get_observability_info():
    """
    Get information about the observability system.
    """
    dashboard = agent_observer.get_dashboard_data()
    
    return {
        "name": "Agent Observability System",
        "version": "1.0.0",
        "description": "Monitor, trace, and analyze AI agent operations",
        
        "endpoints": [
            {"path": "/dashboard", "method": "GET", "description": "Full dashboard data"},
            {"path": "/dashboard/html", "method": "GET", "description": "Visual HTML dashboard"},
            {"path": "/traces", "method": "GET", "description": "List traces"},
            {"path": "/traces/active", "method": "GET", "description": "Active traces"},
            {"path": "/traces/{id}", "method": "GET", "description": "Get specific trace"},
            {"path": "/stats", "method": "GET", "description": "Aggregated statistics"},
            {"path": "/stats/tools", "method": "GET", "description": "Tool usage stats"},
            {"path": "/stats/models", "method": "GET", "description": "Model usage stats"},
            {"path": "/stats/cost", "method": "GET", "description": "Cost breakdown"},
            {"path": "/errors", "method": "GET", "description": "Recent errors"},
            {"path": "/stream", "method": "GET", "description": "Real-time event stream"}
        ],
        
        "stats": {
            "total_executions": dashboard["summary"]["total_executions"],
            "active_traces": dashboard["summary"]["active_traces"],
            "total_tokens": dashboard["summary"]["total_tokens"],
            "total_cost": dashboard["summary"]["total_cost"]
        }
    }

