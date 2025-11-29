"""
Export API - Download conversations as PDF/Markdown/JSON.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import io

from modules.rag import rag_engine


router = APIRouter()


class ExportMessage(BaseModel):
    """Message for export."""
    role: str
    content: str
    timestamp: Optional[str] = None
    sources: Optional[List[dict]] = None


class ExportRequest(BaseModel):
    """Export request."""
    conversation_id: Optional[str] = None
    messages: Optional[List[ExportMessage]] = None
    title: Optional[str] = "GoAI Chat Export"
    include_sources: bool = True
    include_metadata: bool = True


@router.post("/markdown")
async def export_markdown(request: ExportRequest):
    """
    Export conversation as Markdown.
    
    Returns a .md file download.
    """
    messages = await _get_messages(request)
    
    if not messages:
        raise HTTPException(status_code=400, detail="No messages to export")
    
    md = _generate_markdown(messages, request.title, request.include_sources, request.include_metadata)
    
    return Response(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="chat_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md"'
        }
    )


@router.post("/json")
async def export_json(request: ExportRequest):
    """
    Export conversation as JSON.
    
    Returns a .json file download.
    """
    messages = await _get_messages(request)
    
    if not messages:
        raise HTTPException(status_code=400, detail="No messages to export")
    
    export_data = {
        "title": request.title,
        "exported_at": datetime.now().isoformat(),
        "message_count": len(messages),
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp,
                "sources": m.sources if request.include_sources else None
            }
            for m in messages
        ]
    }
    
    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="chat_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        }
    )


@router.post("/html")
async def export_html(request: ExportRequest):
    """
    Export conversation as styled HTML.
    
    Returns a .html file download.
    """
    messages = await _get_messages(request)
    
    if not messages:
        raise HTTPException(status_code=400, detail="No messages to export")
    
    html = _generate_html(messages, request.title, request.include_sources)
    
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="chat_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html"'
        }
    )


@router.post("/text")
async def export_text(request: ExportRequest):
    """
    Export conversation as plain text.
    
    Returns a .txt file download.
    """
    messages = await _get_messages(request)
    
    if not messages:
        raise HTTPException(status_code=400, detail="No messages to export")
    
    lines = [f"# {request.title}", f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    
    for m in messages:
        role = "USER" if m.role == "user" else "ASSISTANT"
        lines.append(f"[{role}]")
        lines.append(m.content)
        lines.append("")
    
    return Response(
        content="\n".join(lines),
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="chat_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"'
        }
    )


async def _get_messages(request: ExportRequest) -> List[ExportMessage]:
    """Get messages from conversation ID or request body."""
    if request.messages:
        return request.messages
    
    if request.conversation_id:
        conv = rag_engine.get_conversation(request.conversation_id)
        if conv:
            return [
                ExportMessage(
                    role=m.role,
                    content=m.content,
                    timestamp=m.timestamp.isoformat() if m.timestamp else None,
                    sources=[{"content": s.content[:200]} for s in m.sources] if m.sources else None
                )
                for m in conv.messages
            ]
    
    return []


def _generate_markdown(messages: List[ExportMessage], title: str, include_sources: bool, include_metadata: bool) -> str:
    """Generate Markdown from messages."""
    lines = [
        f"# {title}",
        "",
    ]
    
    if include_metadata:
        lines.extend([
            f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Messages:** {len(messages)}",
            "",
            "---",
            ""
        ])
    
    for i, m in enumerate(messages):
        if m.role == "user":
            lines.append(f"## 👤 User")
        else:
            lines.append(f"## 🤖 Assistant")
        
        if m.timestamp and include_metadata:
            lines.append(f"*{m.timestamp}*")
        
        lines.append("")
        lines.append(m.content)
        lines.append("")
        
        if include_sources and m.sources:
            lines.append("### 📚 Sources")
            for j, source in enumerate(m.sources, 1):
                content = source.get("content", "")[:150]
                lines.append(f"{j}. {content}...")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def _generate_html(messages: List[ExportMessage], title: str, include_sources: bool) -> str:
    """Generate styled HTML from messages."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e17;
            color: #f1f5f9;
            padding: 40px;
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{
            color: #00d4ff;
            margin-bottom: 8px;
        }}
        .meta {{
            color: #64748b;
            font-size: 14px;
            margin-bottom: 32px;
        }}
        .message {{
            margin-bottom: 24px;
            padding: 20px;
            border-radius: 12px;
        }}
        .user {{
            background: #1a2332;
            border-left: 4px solid #7c3aed;
        }}
        .assistant {{
            background: #111827;
            border-left: 4px solid #00d4ff;
        }}
        .role {{
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .user .role {{ color: #7c3aed; }}
        .assistant .role {{ color: #00d4ff; }}
        .content {{
            line-height: 1.6;
            white-space: pre-wrap;
        }}
        .sources {{
            margin-top: 16px;
            padding: 12px;
            background: rgba(0, 212, 255, 0.1);
            border-radius: 8px;
            font-size: 13px;
        }}
        .sources-title {{
            color: #00d4ff;
            font-weight: 500;
            margin-bottom: 8px;
        }}
        .source-item {{
            color: #94a3b8;
            margin: 4px 0;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="meta">
        Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
        {len(messages)} messages
    </div>
"""
    
    for m in messages:
        role_class = m.role
        role_icon = "👤" if m.role == "user" else "🤖"
        role_name = "User" if m.role == "user" else "Assistant"
        
        html += f"""
    <div class="message {role_class}">
        <div class="role">{role_icon} {role_name}</div>
        <div class="content">{_escape_html(m.content)}</div>
"""
        
        if include_sources and m.sources:
            html += """
        <div class="sources">
            <div class="sources-title">📚 Sources</div>
"""
            for i, source in enumerate(m.sources, 1):
                content = source.get("content", "")[:100]
                html += f'            <div class="source-item">{i}. {_escape_html(content)}...</div>\n'
            html += "        </div>\n"
        
        html += "    </div>\n"
    
    html += """
</body>
</html>"""
    
    return html


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;"))

