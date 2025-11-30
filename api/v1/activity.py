"""
Activity Log API Router

Aggregates logs from all use cases for dashboard display.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/activity", tags=["Activity"])

# Database paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")
KYC_DB = os.path.join(DATA_DIR, "customer_kyc.db")
EBC_DB = os.path.join(DATA_DIR, "ebc_tickets.db")
FEEDBACK_DB = os.path.join(DATA_DIR, "feedback.db")
MEMORY_DB = os.path.join(DATA_DIR, "memories.db")


class ActivityItem(BaseModel):
    """Single activity log entry."""
    id: str
    use_case: str
    action: str
    status: str
    summary: str
    user_id: str
    created_at: str
    metadata: Optional[dict] = None


class ActivityResponse(BaseModel):
    """Activity log response."""
    items: List[ActivityItem]
    total: int
    use_cases: dict


def _get_db_connection(db_path: str):
    """Get database connection if exists."""
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    return None


@router.get("/logs")
async def get_activity_logs(
    limit: int = Query(default=50, le=200),
    use_case: Optional[str] = None,
    hours: int = Query(default=24, le=168),  # Max 7 days
):
    """
    Get aggregated activity logs from all use cases.
    
    Returns recent activity from:
    - KYC verifications
    - EBC ticket analyses
    - User feedback
    - Memory operations
    """
    activities = []
    use_case_counts = {
        "kyc": 0,
        "ebc_tickets": 0,
        "feedback": 0,
        "memory": 0,
    }
    
    cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    
    # KYC Cases
    if (use_case is None or use_case == "kyc") and os.path.exists(KYC_DB):
        try:
            conn = _get_db_connection(KYC_DB)
            if conn:
                cursor = conn.execute("""
                    SELECT id, customer_id, user_id, status, risk_level, 
                           overall_score, request_data, created_at
                    FROM kyc_cases 
                    WHERE created_at > ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (cutoff_time, limit))
                
                for row in cursor.fetchall():
                    request_data = json.loads(row["request_data"])
                    customer = request_data.get("customer", {})
                    customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                    
                    activities.append(ActivityItem(
                        id=row["id"],
                        use_case="kyc",
                        action="KYC Verification",
                        status=row["status"],
                        summary=f"{customer_name or 'Customer'} - Score: {row['overall_score']}, Risk: {row['risk_level']}",
                        user_id=row["user_id"],
                        created_at=row["created_at"],
                        metadata={
                            "customer_name": customer_name,
                            "risk_level": row["risk_level"],
                            "score": row["overall_score"],
                        }
                    ))
                    use_case_counts["kyc"] += 1
                conn.close()
        except Exception as e:
            print(f"Error reading KYC logs: {e}")
    
    # EBC Tickets
    if (use_case is None or use_case == "ebc_tickets") and os.path.exists(EBC_DB):
        try:
            conn = _get_db_connection(EBC_DB)
            if conn:
                cursor = conn.execute("""
                    SELECT id, user_id, subject, sentiment, category, 
                           priority, status, created_at
                    FROM tickets 
                    WHERE created_at > ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (cutoff_time, limit))
                
                for row in cursor.fetchall():
                    activities.append(ActivityItem(
                        id=row["id"],
                        use_case="ebc_tickets",
                        action="Ticket Analysis",
                        status=row["status"] or "analyzed",
                        summary=f"{row['subject'][:50]}... - {row['sentiment']}, {row['priority']} priority",
                        user_id=row["user_id"],
                        created_at=row["created_at"],
                        metadata={
                            "sentiment": row["sentiment"],
                            "category": row["category"],
                            "priority": row["priority"],
                        }
                    ))
                    use_case_counts["ebc_tickets"] += 1
                conn.close()
        except Exception as e:
            print(f"Error reading EBC logs: {e}")
    
    # Feedback
    if (use_case is None or use_case == "feedback") and os.path.exists(FEEDBACK_DB):
        try:
            conn = _get_db_connection(FEEDBACK_DB)
            if conn:
                cursor = conn.execute("""
                    SELECT id, user_id, rating, query, model, created_at
                    FROM feedback 
                    WHERE created_at > ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (cutoff_time, limit))
                
                for row in cursor.fetchall():
                    rating = "positive" if row["rating"] == "positive" else "negative"
                    activities.append(ActivityItem(
                        id=row["id"],
                        use_case="feedback",
                        action="User Feedback",
                        status=rating,
                        summary=f"{'👍' if rating == 'positive' else '👎'} {row['query'][:50]}...",
                        user_id=row["user_id"],
                        created_at=row["created_at"],
                        metadata={
                            "rating": rating,
                            "model": row["model"],
                        }
                    ))
                    use_case_counts["feedback"] += 1
                conn.close()
        except Exception as e:
            print(f"Error reading feedback logs: {e}")
    
    # Memory Operations
    if (use_case is None or use_case == "memory") and os.path.exists(MEMORY_DB):
        try:
            conn = _get_db_connection(MEMORY_DB)
            if conn:
                cursor = conn.execute("""
                    SELECT id, user_id, memory_type, category, content, created_at
                    FROM memories 
                    WHERE created_at > ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (cutoff_time, limit))
                
                for row in cursor.fetchall():
                    activities.append(ActivityItem(
                        id=row["id"],
                        use_case="memory",
                        action="Memory Created",
                        status="active",
                        summary=f"[{row['memory_type']}] {row['content'][:50]}...",
                        user_id=row["user_id"],
                        created_at=row["created_at"],
                        metadata={
                            "type": row["memory_type"],
                            "category": row["category"],
                        }
                    ))
                    use_case_counts["memory"] += 1
                conn.close()
        except Exception as e:
            print(f"Error reading memory logs: {e}")
    
    # Sort all by created_at descending
    activities.sort(key=lambda x: x.created_at, reverse=True)
    
    # Limit total
    activities = activities[:limit]
    
    return ActivityResponse(
        items=activities,
        total=len(activities),
        use_cases=use_case_counts
    )


@router.get("/summary")
async def get_activity_summary(hours: int = Query(default=24, le=168)):
    """
    Get summary statistics for all use cases.
    """
    cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    summary = {
        "kyc": {"total": 0, "approved": 0, "rejected": 0, "pending": 0},
        "ebc_tickets": {"total": 0, "positive": 0, "negative": 0, "neutral": 0},
        "feedback": {"total": 0, "positive": 0, "negative": 0},
        "memory": {"total": 0, "short": 0, "medium": 0, "long": 0},
    }
    
    # KYC Summary
    if os.path.exists(KYC_DB):
        try:
            conn = _get_db_connection(KYC_DB)
            if conn:
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM kyc_cases 
                    WHERE created_at > ?
                    GROUP BY status
                """, (cutoff_time,))
                for row in cursor.fetchall():
                    summary["kyc"]["total"] += row["count"]
                    if row["status"] == "approved":
                        summary["kyc"]["approved"] = row["count"]
                    elif row["status"] == "rejected":
                        summary["kyc"]["rejected"] = row["count"]
                    else:
                        summary["kyc"]["pending"] += row["count"]
                conn.close()
        except:
            pass
    
    # EBC Summary
    if os.path.exists(EBC_DB):
        try:
            conn = _get_db_connection(EBC_DB)
            if conn:
                cursor = conn.execute("""
                    SELECT sentiment, COUNT(*) as count 
                    FROM tickets 
                    WHERE created_at > ?
                    GROUP BY sentiment
                """, (cutoff_time,))
                for row in cursor.fetchall():
                    summary["ebc_tickets"]["total"] += row["count"]
                    if row["sentiment"] == "positive":
                        summary["ebc_tickets"]["positive"] = row["count"]
                    elif row["sentiment"] == "negative":
                        summary["ebc_tickets"]["negative"] = row["count"]
                    else:
                        summary["ebc_tickets"]["neutral"] += row["count"]
                conn.close()
        except:
            pass
    
    # Feedback Summary
    if os.path.exists(FEEDBACK_DB):
        try:
            conn = _get_db_connection(FEEDBACK_DB)
            if conn:
                cursor = conn.execute("""
                    SELECT rating, COUNT(*) as count 
                    FROM feedback 
                    WHERE created_at > ?
                    GROUP BY rating
                """, (cutoff_time,))
                for row in cursor.fetchall():
                    summary["feedback"]["total"] += row["count"]
                    if row["rating"] == "positive":
                        summary["feedback"]["positive"] = row["count"]
                    else:
                        summary["feedback"]["negative"] = row["count"]
                conn.close()
        except:
            pass
    
    # Memory Summary
    if os.path.exists(MEMORY_DB):
        try:
            conn = _get_db_connection(MEMORY_DB)
            if conn:
                cursor = conn.execute("""
                    SELECT memory_type, COUNT(*) as count 
                    FROM memories 
                    WHERE created_at > ?
                    GROUP BY memory_type
                """, (cutoff_time,))
                for row in cursor.fetchall():
                    summary["memory"]["total"] += row["count"]
                    if row["memory_type"] == "short":
                        summary["memory"]["short"] = row["count"]
                    elif row["memory_type"] == "medium":
                        summary["memory"]["medium"] = row["count"]
                    else:
                        summary["memory"]["long"] = row["count"]
                conn.close()
        except:
            pass
    
    return {
        "period_hours": hours,
        "summary": summary,
        "total_activities": sum(s["total"] for s in summary.values()),
    }

