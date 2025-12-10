"""
ESG Companion Agent

An intelligent AI assistant that has access to:
- Knowledge Base (RAG) - sustainability standards, best practices
- SQL Database - company emissions, ESG scores, documents
- Analytics - trends, calculations, insights
- LLM - natural conversation and reasoning
- Memory System - persistent conversation history

This agent can answer questions about:
- Company carbon footprint and emissions
- ESG scores and performance
- Sustainability best practices
- Document status and analysis
- Reduction recommendations
"""

import json
import sqlite3
import secrets
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from core.llm.router import LLMRouter


# Conversation history database
CONVERSATION_DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/companion_conversations.db")
os.makedirs(os.path.dirname(CONVERSATION_DB_PATH), exist_ok=True)


def init_conversation_db():
    """Initialize the conversation database - Platform-level, supports all use cases."""
    conn = sqlite3.connect(CONVERSATION_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            company_id TEXT,
            agent_type TEXT DEFAULT 'esg_companion',
            title TEXT,
            context_data TEXT,
            tags TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            message_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_results TEXT,
            attachments TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)
    # Migrate: Add agent_type column if not exists
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN agent_type TEXT DEFAULT 'esg_companion'")
    except:
        pass  # Column already exists
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN context_data TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN tags TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN attachments TEXT")
    except:
        pass
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_agent ON conversations(agent_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)")
    conn.commit()
    conn.close()


# Initialize on module load
init_conversation_db()


@dataclass
class ESGContext:
    """Context about the user's company and permissions."""
    company_id: str = "xyz-corp-001"
    user_email: str = "user@company.com"
    role: str = "admin"
    conversation_id: Optional[str] = None
    

class ESGCompanionAgent:
    """
    ESG Companion - Your AI sustainability expert.
    
    Capabilities:
    - Query emissions data
    - Search knowledge base
    - Analyze documents
    - Provide recommendations
    - Answer ESG questions
    """
    
    SYSTEM_PROMPT = """You are the ESG Companion, an expert AI assistant for the SustainData platform - a comprehensive sustainability data management system.

## 🏢 About SustainData Platform
You are integrated into a platform that helps companies track, manage, and reduce their carbon footprint. You can:
- Access all uploaded sustainability documents
- Query emissions data and statistics
- Search the knowledge base for ESG standards
- Calculate CO2e for various activities
- Guide users through platform features

## 📍 Platform Features & Navigation
When users ask about how to do something, guide them to the right place:

### Upload Documents (📤 /upload)
- Users can drag & drop ANY document: utility bills, flight receipts, shipping invoices, ESG reports
- AI automatically extracts data and calculates CO2e
- Supports: PDF, images (PNG, JPG), Excel, text files
- Example: "To upload a document, go to **Upload Documents** in the sidebar or click 📤"

### My Submissions (📋 /submissions)  
- View all uploaded documents and their status
- See: Pending review, Approved, Auto-approved, Needs attention
- Track total CO2e from approved documents
- Example: "Check **My Submissions** to see your document status"

### Review Queue (✅ /review) - Supervisors/Admins
- Review AI-extracted data before approval
- Edit extracted values if needed
- Approve or reject documents
- Example: "Documents with <95% confidence need manual review"

### Analytics (📊 /analytics) - Supervisors/Admins
- View emissions trends over time
- Category breakdown (travel, energy, shipping)
- Scope 1/2/3 distribution
- Top contributors

### ESG Companion (🤖 /companion) - That's me!
- Chat about emissions data
- Get recommendations
- Calculate CO2e for activities
- Learn about ESG standards

## 🔧 Available Tools
1. **query_emissions** - Get emissions data from the database
2. **query_documents** - Search uploaded documents  
3. **query_knowledge** - Search sustainability knowledge base (GRI, TCFD, SBTi)
4. **get_company_stats** - Get company ESG statistics
5. **calculate_emissions** - Calculate CO2e for electricity, fuel, travel, etc.

## 📝 Common Workflows

### "How do I track my carbon footprint?"
1. Go to **Upload Documents** 
2. Upload utility bills, travel receipts, fuel receipts
3. AI extracts data and calculates CO2e automatically
4. High-confidence docs are auto-approved
5. View total in **My Submissions** or **Dashboard**

### "How do I add a flight?"
1. Take a photo of your boarding pass or receipt
2. Go to **Upload Documents**
3. Drop the image - AI detects it's a flight receipt
4. CO2e is calculated based on route and class
5. Check status in **My Submissions**

### "What document types are supported?"
- ⚡ Utility bills (electricity, gas, water)
- ✈️ Flight receipts/boarding passes
- 🚗 Fuel receipts
- 📦 Shipping invoices
- 🏭 ESG reports
- 📄 Any other sustainability document (AI learns new types!)

## 💡 Pro Tips to Share
- "Tip: High-confidence documents (>95%) are auto-approved!"
- "Tip: You can upload multiple documents at once"
- "Tip: The AI learns new document types automatically"
- "Tip: All data is organized by Scope 1, 2, and 3"

## 🎯 Your Role
- Answer ESG questions with context from their data
- Guide users to the right platform features
- Calculate emissions when asked
- Explain ESG concepts simply
- Provide actionable recommendations
- Celebrate their sustainability progress! 🌱

## 📏 Guidelines
- Be helpful, friendly, and encouraging
- Format numbers clearly: "1,234 kg CO₂e" or "1.23 tonnes"
- When guiding to features, mention the sidebar menu item
- If they seem lost, ask what they're trying to accomplish
- Always suggest relevant next steps
- Use emojis thoughtfully for clarity

## Response Format
- Start with a direct answer
- Provide context if helpful
- Suggest next steps or related features
- Keep responses concise but complete
"""

    def __init__(self, db_path: str = "data/sustainability_unified.db"):
        self.db_path = db_path
        self.llm_router: Optional[LLMRouter] = None
        self.rag_engine = None
        self.conversation_history: List[Dict[str, str]] = []
        self.current_conversation_id: Optional[str] = None
        
    def set_llm_router(self, router: LLMRouter):
        """Set the LLM router for chat capabilities."""
        self.llm_router = router
        
    def set_rag_engine(self, rag):
        """Set the RAG engine for knowledge base queries."""
        self.rag_engine = rag
        
    def _get_db_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _get_conversation_db(self):
        """Get conversation database connection."""
        return sqlite3.connect(CONVERSATION_DB_PATH)
    
    # ==================== CONVERSATION MANAGEMENT ====================
    
    def create_conversation(
        self, 
        user_id: str, 
        company_id: str = None, 
        title: str = None,
        agent_type: str = "esg_companion",
        context_data: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> str:
        """Create a new conversation - supports any agent/use case."""
        conv_id = f"conv_{secrets.token_hex(8)}"
        now = datetime.now().isoformat()
        
        conn = self._get_conversation_db()
        conn.execute("""
            INSERT INTO conversations (id, user_id, company_id, agent_type, title, context_data, tags, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            conv_id, 
            user_id, 
            company_id, 
            agent_type,
            title or "New Conversation", 
            json.dumps(context_data) if context_data else None,
            json.dumps(tags) if tags else None,
            now, 
            now
        ))
        conn.commit()
        conn.close()
        
        self.current_conversation_id = conv_id
        self.conversation_history = []
        return conv_id
    
    def get_conversations(
        self, 
        user_id: str, 
        limit: int = 20,
        agent_type: str = None
    ) -> List[Dict[str, Any]]:
        """Get user's conversation history - optionally filtered by agent type."""
        conn = self._get_conversation_db()
        conn.row_factory = sqlite3.Row
        
        if agent_type:
            rows = conn.execute("""
                SELECT c.*, 
                       (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message
                FROM conversations c
                WHERE user_id = ? AND agent_type = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user_id, agent_type, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT c.*, 
                       (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message
                FROM conversations c
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
        
        conn.close()
        
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "agent_type": row["agent_type"] if "agent_type" in row.keys() else "esg_companion",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": row["message_count"],
                "last_message": row["last_message"][:100] + "..." if row["last_message"] and len(row["last_message"]) > 100 else row["last_message"]
            }
            for row in rows
        ]
    
    def get_conversation_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages from a conversation."""
        conn = self._get_conversation_db()
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute("""
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ?
        """, (conversation_id, limit)).fetchall()
        
        conn.close()
        
        messages = []
        for row in rows:
            msg = {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"],
            }
            if row["tool_results"]:
                try:
                    msg["tool_results"] = json.loads(row["tool_results"])
                except:
                    pass
            messages.append(msg)
        
        return messages
    
    def load_conversation(self, conversation_id: str) -> bool:
        """Load a conversation into memory."""
        messages = self.get_conversation_messages(conversation_id)
        if not messages:
            return False
        
        self.current_conversation_id = conversation_id
        self.conversation_history = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]
        return True
    
    def _save_message(self, conversation_id: str, role: str, content: str, tool_results: Dict = None):
        """Save a message to the conversation."""
        msg_id = f"msg_{secrets.token_hex(8)}"
        now = datetime.now().isoformat()
        
        conn = self._get_conversation_db()
        conn.execute("""
            INSERT INTO messages (id, conversation_id, role, content, tool_results, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            msg_id,
            conversation_id,
            role,
            content,
            json.dumps(tool_results) if tool_results else None,
            now
        ))
        
        # Update conversation
        conn.execute("""
            UPDATE conversations 
            SET updated_at = ?, message_count = message_count + 1
            WHERE id = ?
        """, (now, conversation_id))
        
        # Update title from first user message
        if role == "user":
            conn.execute("""
                UPDATE conversations 
                SET title = CASE WHEN message_count <= 2 THEN ? ELSE title END
                WHERE id = ?
            """, (content[:50] + "..." if len(content) > 50 else content, conversation_id))
        
        conn.commit()
        conn.close()
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages."""
        conn = self._get_conversation_db()
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        result = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        deleted = result.rowcount > 0
        conn.commit()
        conn.close()
        
        if deleted and self.current_conversation_id == conversation_id:
            self.current_conversation_id = None
            self.conversation_history = []
        
        return deleted
    
    # ==================== TOOL IMPLEMENTATIONS ====================
    
    def query_emissions(self, company_id: str = None, category: str = None, 
                       scope: str = None, limit: int = 20) -> Dict[str, Any]:
        """Query emissions data from the database."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT document_type, category, calculated_co2e_kg, status, 
                   filename, uploaded_at, confidence
            FROM emission_documents 
            WHERE status IN ('approved', 'auto_approved')
        """
        params = []
        
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        if category:
            query += " AND category LIKE ?"
            params.append(f"%{category}%")
            
        query += f" ORDER BY uploaded_at DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        columns = ['document_type', 'category', 'co2e_kg', 'status', 
                   'filename', 'uploaded_at', 'confidence']
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Also get totals
        cursor.execute("""
            SELECT 
                COUNT(*) as total_docs,
                SUM(calculated_co2e_kg) as total_co2e,
                AVG(confidence) as avg_confidence
            FROM emission_documents 
            WHERE status IN ('approved', 'auto_approved')
        """)
        totals = cursor.fetchone()
        
        conn.close()
        
        return {
            "documents": results,
            "summary": {
                "total_documents": totals[0] or 0,
                "total_co2e_kg": totals[1] or 0,
                "total_co2e_tonnes": (totals[1] or 0) / 1000,
                "avg_confidence": round((totals[2] or 0) * 100, 1)
            }
        }
    
    def query_documents(self, search_term: str = None, status: str = None,
                       doc_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search uploaded documents."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM emission_documents WHERE 1=1"
        params = []
        
        if search_term:
            query += " AND (filename LIKE ? OR raw_text LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        if status:
            query += " AND status = ?"
            params.append(status)
        if doc_type:
            query += " AND document_type LIKE ?"
            params.append(f"%{doc_type}%")
            
        query += f" ORDER BY uploaded_at DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_company_stats(self, company_id: str = None) -> Dict[str, Any]:
        """Get comprehensive company statistics."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Document counts
        cursor.execute("""
            SELECT status, COUNT(*), SUM(calculated_co2e_kg)
            FROM emission_documents
            GROUP BY status
        """)
        status_data = cursor.fetchall()
        stats['documents'] = {row[0]: {'count': row[1], 'co2e_kg': row[2] or 0} 
                            for row in status_data}
        
        # Emissions by category
        cursor.execute("""
            SELECT document_type, COUNT(*), SUM(calculated_co2e_kg)
            FROM emission_documents
            WHERE status IN ('approved', 'auto_approved')
            GROUP BY document_type
            ORDER BY SUM(calculated_co2e_kg) DESC
        """)
        category_data = cursor.fetchall()
        stats['by_category'] = [
            {'category': row[0], 'count': row[1], 'co2e_kg': row[2] or 0}
            for row in category_data
        ]
        
        # Emissions by scope
        cursor.execute("""
            SELECT emission_scope, SUM(co2e_kg)
            FROM emission_entries
            GROUP BY emission_scope
        """)
        scope_data = dict(cursor.fetchall())
        stats['by_scope'] = {
            'scope_1': scope_data.get('scope_1', 0) or 0,
            'scope_2': scope_data.get('scope_2', 0) or 0,
            'scope_3': scope_data.get('scope_3', 0) or 0,
        }
        stats['total_co2e_kg'] = sum(stats['by_scope'].values())
        stats['total_co2e_tonnes'] = stats['total_co2e_kg'] / 1000
        
        # Recent activity
        cursor.execute("""
            SELECT document_type, filename, calculated_co2e_kg, uploaded_at
            FROM emission_documents
            WHERE status IN ('approved', 'auto_approved')
            ORDER BY uploaded_at DESC
            LIMIT 5
        """)
        stats['recent_activity'] = [
            {'type': row[0], 'filename': row[1], 'co2e_kg': row[2], 'date': row[3]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return stats
    
    def query_knowledge(self, question: str) -> str:
        """Search the knowledge base using RAG."""
        if self.rag_engine:
            try:
                # Use RAG to find relevant information
                result = self.rag_engine.query(question)
                return result.get('response', 'No relevant information found.')
            except:
                pass
        return "Knowledge base not available."
    
    def calculate_emissions(self, activity_type: str, value: float, unit: str) -> Dict[str, Any]:
        """Calculate CO2e for various activities."""
        # Emission factors (kg CO2e per unit)
        emission_factors = {
            "electricity": {"kwh": 0.42, "mwh": 420},
            "natural_gas": {"therm": 5.3, "ccf": 5.3, "kwh": 0.18},
            "gasoline": {"gallon": 8.89, "liter": 2.35},
            "diesel": {"gallon": 10.21, "liter": 2.70},
            "flight_domestic": {"mile": 0.255, "km": 0.158},
            "flight_international": {"mile": 0.195, "km": 0.121},
            "car": {"mile": 0.404, "km": 0.251},
            "shipping": {"kg_km": 0.0001, "ton_mile": 0.161},
        }
        
        activity = activity_type.lower().replace(" ", "_")
        unit = unit.lower()
        
        if activity in emission_factors:
            factors = emission_factors[activity]
            if unit in factors:
                co2e_kg = value * factors[unit]
                return {
                    "activity": activity_type,
                    "value": value,
                    "unit": unit,
                    "co2e_kg": round(co2e_kg, 2),
                    "co2e_tonnes": round(co2e_kg / 1000, 4),
                    "emission_factor": factors[unit],
                    "calculation": f"{value} {unit} × {factors[unit]} kg CO₂e/{unit} = {round(co2e_kg, 2)} kg CO₂e"
                }
        
        return {
            "error": f"Unknown activity or unit: {activity_type} ({unit})",
            "available_activities": list(emission_factors.keys())
        }
    
    # ==================== CHAT INTERFACE ====================
    
    def _build_context(self, context: ESGContext) -> str:
        """Build context string from current data."""
        stats = self.get_company_stats(context.company_id)
        
        context_parts = [
            f"## Current Company Data (as of {datetime.now().strftime('%Y-%m-%d %H:%M')})",
            f"- Total CO₂e: {stats['total_co2e_tonnes']:.2f} tonnes",
            f"- Scope 1: {stats['by_scope']['scope_1']/1000:.2f}t | Scope 2: {stats['by_scope']['scope_2']/1000:.2f}t | Scope 3: {stats['by_scope']['scope_3']/1000:.2f}t",
            "",
            "### Emissions by Category:"
        ]
        
        for cat in stats.get('by_category', [])[:5]:
            name = cat['category'].replace('_', ' ').title() if cat['category'] else 'Other'
            context_parts.append(f"- {name}: {cat['co2e_kg']/1000:.2f}t ({cat['count']} documents)")
        
        context_parts.extend([
            "",
            "### Recent Activity:"
        ])
        
        for activity in stats.get('recent_activity', [])[:3]:
            context_parts.append(f"- {activity['type'].replace('_', ' ').title()}: {activity['co2e_kg']:.1f} kg")
        
        return "\n".join(context_parts)
    
    async def chat(
        self,
        message: str,
        context: ESGContext = None,
        model: str = "gpt-4o-mini",
        include_data_context: bool = True,
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """
        Chat with the ESG Companion.
        
        Args:
            message: User's message
            context: User context (company, permissions)
            model: LLM model to use
            include_data_context: Whether to include current data in context
            conversation_id: Existing conversation ID to continue
        
        Returns:
            Response with answer and any tool results
        """
        if not self.llm_router:
            return {
                "response": "I'm not fully configured yet. Please try again later.",
                "status": "error"
            }
        
        context = context or ESGContext()
        
        # Handle conversation persistence
        if conversation_id:
            # Load existing conversation
            if conversation_id != self.current_conversation_id:
                self.load_conversation(conversation_id)
        elif not self.current_conversation_id:
            # Create new conversation
            conversation_id = self.create_conversation(
                user_id=context.user_email,
                company_id=context.company_id
            )
        else:
            conversation_id = self.current_conversation_id
        
        # Build messages
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        # Add data context
        if include_data_context:
            data_context = self._build_context(context)
            messages.append({
                "role": "system",
                "content": f"Here is the current data for context:\n\n{data_context}"
            })
        
        # Add conversation history (last 10 messages)
        messages.extend(self.conversation_history[-10:])
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Check if message needs tool use
        tool_results = {}
        lower_msg = message.lower()
        
        # System navigation queries - provide system help
        if any(phrase in lower_msg for phrase in ['how do i', 'how can i', 'where do i', 'how to', 'walk me through', 'help me']):
            if any(word in lower_msg for word in ['upload', 'add', 'submit', 'track']):
                tool_results['system_help'] = self.get_system_help('upload')
            elif any(word in lower_msg for word in ['submission', 'status', 'my document', 'pending', 'approved']):
                tool_results['system_help'] = self.get_system_help('submissions')
                tool_results['document_status'] = self.get_document_status_summary()
            elif any(word in lower_msg for word in ['review', 'approve', 'reject']):
                tool_results['system_help'] = self.get_system_help('review')
            elif any(word in lower_msg for word in ['analytic', 'trend', 'report', 'insight']):
                tool_results['system_help'] = self.get_system_help('analytics')
        
        # Document type queries
        if any(phrase in lower_msg for phrase in ['what type', 'what document', 'what can i upload', 'supported', 'accept']):
            tool_results['system_help'] = self.get_system_help('upload')
        
        # Status check queries
        if any(phrase in lower_msg for phrase in ['pending', 'status', 'waiting', 'review queue', 'my submission']):
            tool_results['document_status'] = self.get_document_status_summary()
        
        # Auto-detect data queries
        if any(word in lower_msg for word in ['emissions', 'carbon', 'co2', 'footprint', 'total', 'scope']):
            tool_results['emissions_data'] = self.query_emissions(context.company_id)
        
        if any(word in lower_msg for word in ['document', 'file', 'receipt', 'bill', 'invoice']) and 'type' not in lower_msg:
            tool_results['documents'] = self.query_documents(limit=5)
        
        if any(word in lower_msg for word in ['calculate', 'how much', 'estimate']) and any(w in lower_msg for w in ['kwh', 'mile', 'gallon', 'flight', 'drive', 'electricity']):
            # Calculation context will be handled by LLM
            pass
        
        if any(word in lower_msg for word in ['standard', 'requirement', 'regulation', 'best practice', 'gri', 'tcfd', 'sbti']):
            if self.rag_engine:
                try:
                    rag_result = await self.rag_engine.aquery(message)
                    tool_results['knowledge'] = rag_result.get('response', '')
                except:
                    pass
        
        # Add tool results to context if any
        if tool_results:
            tool_context = "\n\n## Tool Results:\n"
            for tool, result in tool_results.items():
                tool_context += f"\n### {tool}:\n```json\n{json.dumps(result, indent=2, default=str)[:2000]}\n```\n"
            messages.append({
                "role": "system",
                "content": tool_context
            })
        
        # Get LLM response
        try:
            response = await self.llm_router.run(
                model_id=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            
            if response.get("status") == "success":
                assistant_message = response["content"]
                
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append({"role": "assistant", "content": assistant_message})
                
                # Save to database
                if conversation_id:
                    self._save_message(conversation_id, "user", message)
                    self._save_message(conversation_id, "assistant", assistant_message, tool_results)
                
                return {
                    "response": assistant_message,
                    "status": "success",
                    "tool_results": tool_results if tool_results else None,
                    "model": response.get("model", model),
                    "conversation_id": conversation_id
                }
            else:
                return {
                    "response": f"I encountered an issue: {response.get('error', 'Unknown error')}",
                    "status": "error",
                    "conversation_id": conversation_id
                }
                
        except Exception as e:
            return {
                "response": f"Sorry, I encountered an error: {str(e)}",
                "status": "error",
                "conversation_id": conversation_id
            }
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def get_suggestions(self) -> List[str]:
        """Get conversation starter suggestions."""
        return [
            "What's my total carbon footprint?",
            "How do I upload a document?",
            "Show me my emissions by category",
            "What documents are pending review?",
            "How can I reduce my Scope 3 emissions?",
            "Calculate emissions for 1000 kWh electricity",
            "What document types can I upload?",
            "Walk me through tracking my carbon footprint",
        ]
    
    def get_system_help(self, topic: str = None) -> Dict[str, Any]:
        """Get help about system features."""
        help_topics = {
            "upload": {
                "title": "📤 Upload Documents",
                "route": "/upload",
                "description": "Upload any sustainability document and AI will extract data automatically",
                "steps": [
                    "Go to 'Upload Documents' in the sidebar",
                    "Drag & drop your file or click 'Select Files'",
                    "AI analyzes and extracts data",
                    "Document is added to review queue",
                    "High confidence docs are auto-approved"
                ],
                "supported_types": [
                    "Utility bills (electricity, gas, water)",
                    "Flight receipts & boarding passes",
                    "Fuel receipts",
                    "Shipping invoices",
                    "ESG reports",
                    "Any other document (AI learns new types!)"
                ]
            },
            "submissions": {
                "title": "📋 My Submissions",
                "route": "/submissions",
                "description": "Track all your uploaded documents and their status",
                "statuses": {
                    "pending": "Waiting for reviewer approval",
                    "approved": "Verified and counted in your emissions",
                    "auto_approved": "High confidence - automatically approved",
                    "rejected": "Needs attention - please review and resubmit"
                }
            },
            "review": {
                "title": "✅ Review Queue",
                "route": "/review",
                "description": "Review and approve AI-extracted data (Supervisors/Admins)",
                "actions": ["Approve", "Reject", "Edit data", "Bulk approve"]
            },
            "analytics": {
                "title": "📊 Analytics",
                "route": "/analytics",
                "description": "View emissions trends and insights",
                "features": [
                    "Monthly trends",
                    "Category breakdown",
                    "Scope 1/2/3 distribution",
                    "Top contributors"
                ]
            },
            "companion": {
                "title": "🤖 ESG Companion",
                "route": "/companion",
                "description": "Chat about your data (that's me!)",
                "capabilities": [
                    "Answer ESG questions",
                    "Query your emissions data",
                    "Calculate CO2e for activities",
                    "Provide recommendations"
                ]
            }
        }
        
        if topic and topic.lower() in help_topics:
            return help_topics[topic.lower()]
        return {"topics": help_topics}
    
    def get_document_status_summary(self) -> Dict[str, Any]:
        """Get a summary of document statuses for the user."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                SUM(calculated_co2e_kg) as co2e
            FROM emission_documents
            GROUP BY status
        """)
        
        statuses = {}
        for row in cursor.fetchall():
            status, count, co2e = row
            statuses[status] = {
                "count": count,
                "co2e_kg": co2e or 0,
                "action_needed": status == 'pending' or status == 'rejected'
            }
        
        # Get recent pending
        cursor.execute("""
            SELECT document_type, filename, uploaded_at, confidence
            FROM emission_documents
            WHERE status = 'pending'
            ORDER BY uploaded_at DESC
            LIMIT 5
        """)
        pending_docs = [
            {"type": row[0], "filename": row[1], "uploaded": row[2], "confidence": row[3]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "summary": statuses,
            "pending_documents": pending_docs,
            "total_pending": statuses.get('pending', {}).get('count', 0),
            "needs_attention": statuses.get('rejected', {}).get('count', 0)
        }


# Singleton instance
esg_companion = ESGCompanionAgent()

