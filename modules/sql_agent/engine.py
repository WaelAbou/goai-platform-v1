"""
SQL Agent Engine - Natural language to SQL conversion and execution.
Supports multiple databases with schema introspection.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MSSQL = "mssql"


@dataclass
class TableSchema:
    name: str
    columns: List[Dict[str, Any]] = field(default_factory=list)
    primary_key: Optional[str] = None
    foreign_keys: List[Dict[str, str]] = field(default_factory=list)
    sample_data: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DatabaseSchema:
    name: str
    db_type: DatabaseType
    tables: List[TableSchema] = field(default_factory=list)
    views: List[str] = field(default_factory=list)


@dataclass
class SQLQuery:
    sql: str
    explanation: str
    tables_used: List[str] = field(default_factory=list)
    columns_used: List[str] = field(default_factory=list)
    query_type: str = "SELECT"  # SELECT, INSERT, UPDATE, DELETE, etc.


@dataclass
class SQLResult:
    query: SQLQuery
    data: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    columns: List[str] = field(default_factory=list)
    execution_time_ms: float = 0
    error: Optional[str] = None
    success: bool = True


class SQLAgent:
    """
    Agent for converting natural language to SQL and executing queries.
    """

    # SQL generation prompt template
    SQL_GENERATION_PROMPT = """You are a SQL expert. Convert the following natural language question to SQL.

Database Schema:
{schema}

Question: {question}

Instructions:
1. Write a valid SQL query for {db_type}
2. Only use tables and columns that exist in the schema
3. Use appropriate JOINs when querying multiple tables
4. Add appropriate WHERE clauses for filtering
5. Use ORDER BY and LIMIT when appropriate
6. For aggregations, use GROUP BY correctly

Return ONLY the SQL query, no explanations.
SQL:"""

    SQL_EXPLANATION_PROMPT = """Explain what this SQL query does in simple terms:

SQL Query:
{sql}

Database Schema:
{schema}

Provide a clear, non-technical explanation of what data this query retrieves and how."""

    def __init__(self):
        self.llm_router = None
        self.schemas: Dict[str, DatabaseSchema] = {}
        self.connections: Dict[str, Any] = {}
        self.default_database: Optional[str] = None

    def set_llm_router(self, router):
        """Set the LLM router for SQL generation"""
        self.llm_router = router

    def register_schema(self, schema: DatabaseSchema):
        """Register a database schema"""
        self.schemas[schema.name] = schema
        if self.default_database is None:
            self.default_database = schema.name

    def register_schema_from_dict(self, name: str, schema_dict: Dict[str, Any]):
        """Register schema from a dictionary definition"""
        tables = []
        for table_name, table_info in schema_dict.get("tables", {}).items():
            tables.append(TableSchema(
                name=table_name,
                columns=table_info.get("columns", []),
                primary_key=table_info.get("primary_key"),
                foreign_keys=table_info.get("foreign_keys", []),
                sample_data=table_info.get("sample_data", [])
            ))
        
        schema = DatabaseSchema(
            name=name,
            db_type=DatabaseType(schema_dict.get("type", "sqlite")),
            tables=tables,
            views=schema_dict.get("views", [])
        )
        self.register_schema(schema)

    def _format_schema_for_prompt(self, schema: DatabaseSchema) -> str:
        """Format schema for LLM prompt"""
        lines = [f"Database: {schema.name} ({schema.db_type.value})"]
        lines.append("Tables:")
        
        for table in schema.tables:
            lines.append(f"\n  {table.name}:")
            for col in table.columns:
                col_name = col.get("name", col.get("column_name", ""))
                col_type = col.get("type", col.get("data_type", ""))
                nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
                pk = " PRIMARY KEY" if col_name == table.primary_key else ""
                lines.append(f"    - {col_name}: {col_type} {nullable}{pk}")
            
            if table.foreign_keys:
                lines.append("    Foreign Keys:")
                for fk in table.foreign_keys:
                    lines.append(f"      - {fk.get('column')} -> {fk.get('references')}")
            
            if table.sample_data:
                lines.append(f"    Sample ({len(table.sample_data)} rows):")
                for row in table.sample_data[:2]:
                    lines.append(f"      {row}")
        
        return "\n".join(lines)

    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL query"""
        # Simple extraction - looks for FROM and JOIN clauses
        tables = []
        
        # FROM clause
        from_match = re.findall(r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        tables.extend(from_match)
        
        # JOIN clauses
        join_match = re.findall(r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        tables.extend(join_match)
        
        return list(set(tables))

    def _determine_query_type(self, sql: str) -> str:
        """Determine the type of SQL query"""
        sql_upper = sql.strip().upper()
        for qt in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]:
            if sql_upper.startswith(qt):
                return qt
        return "UNKNOWN"

    def _validate_sql(self, sql: str, schema: DatabaseSchema) -> Tuple[bool, Optional[str]]:
        """Validate SQL against schema"""
        tables_used = self._extract_tables_from_sql(sql)
        schema_tables = {t.name.lower() for t in schema.tables}
        
        for table in tables_used:
            if table.lower() not in schema_tables:
                return False, f"Table '{table}' not found in schema"
        
        # Basic SQL injection prevention
        dangerous_patterns = [
            r';\s*DROP',
            r';\s*DELETE',
            r';\s*UPDATE',
            r';\s*INSERT',
            r'--',
            r'/\*',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return False, "Potentially dangerous SQL pattern detected"
        
        return True, None

    async def generate_sql(
        self,
        question: str,
        database: Optional[str] = None,
        validate: bool = True
    ) -> SQLQuery:
        """
        Generate SQL from a natural language question.
        
        Args:
            question: Natural language question
            database: Database name (uses default if not specified)
            validate: Whether to validate the generated SQL
            
        Returns:
            SQLQuery object with generated SQL
        """
        db_name = database or self.default_database
        
        if db_name is None or db_name not in self.schemas:
            return SQLQuery(
                sql="",
                explanation=f"Database '{db_name}' not found",
                query_type="ERROR"
            )
        
        schema = self.schemas[db_name]
        schema_text = self._format_schema_for_prompt(schema)
        
        if self.llm_router is None:
            # Return a mock query for testing
            return SQLQuery(
                sql="SELECT * FROM example_table LIMIT 10;",
                explanation="LLM router not configured",
                query_type="SELECT"
            )
        
        # Generate SQL using LLM
        prompt = self.SQL_GENERATION_PROMPT.format(
            schema=schema_text,
            question=question,
            db_type=schema.db_type.value
        )
        
        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            sql = response.get("content", "").strip()
            
            # Clean up the SQL
            sql = sql.replace("```sql", "").replace("```", "").strip()
            
            # Validate if requested
            if validate:
                is_valid, error = self._validate_sql(sql, schema)
                if not is_valid:
                    return SQLQuery(
                        sql=sql,
                        explanation=f"Validation error: {error}",
                        query_type="ERROR"
                    )
            
            tables = self._extract_tables_from_sql(sql)
            query_type = self._determine_query_type(sql)
            
            return SQLQuery(
                sql=sql,
                explanation="",  # Will be filled by explain_sql
                tables_used=tables,
                query_type=query_type
            )
        
        except Exception as e:
            return SQLQuery(
                sql="",
                explanation=f"Error generating SQL: {str(e)}",
                query_type="ERROR"
            )

    async def explain_sql(
        self,
        sql: str,
        database: Optional[str] = None
    ) -> str:
        """
        Explain a SQL query in natural language.
        
        Args:
            sql: The SQL query to explain
            database: Database name for context
            
        Returns:
            Natural language explanation
        """
        db_name = database or self.default_database
        schema_text = ""
        
        if db_name and db_name in self.schemas:
            schema_text = self._format_schema_for_prompt(self.schemas[db_name])
        
        if self.llm_router is None:
            return "LLM router not configured for SQL explanation"
        
        prompt = self.SQL_EXPLANATION_PROMPT.format(
            sql=sql,
            schema=schema_text or "Schema not available"
        )
        
        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            return response.get("content", "Unable to explain query")
        
        except Exception as e:
            return f"Error explaining SQL: {str(e)}"

    async def execute(
        self,
        sql: str,
        database: Optional[str] = None,
        max_rows: int = 100
    ) -> SQLResult:
        """
        Execute a SQL query (placeholder - requires database connection).
        
        Args:
            sql: SQL query to execute
            database: Database to query
            max_rows: Maximum rows to return
            
        Returns:
            SQLResult with query results
        """
        # This is a placeholder - actual implementation would connect to a database
        query = SQLQuery(
            sql=sql,
            explanation="Query execution placeholder",
            tables_used=self._extract_tables_from_sql(sql),
            query_type=self._determine_query_type(sql)
        )
        
        return SQLResult(
            query=query,
            data=[],
            row_count=0,
            columns=[],
            error="Database execution not yet implemented - connect a database first",
            success=False
        )

    async def query(
        self,
        question: str,
        database: Optional[str] = None,
        execute: bool = False,
        max_rows: int = 100
    ) -> SQLResult:
        """
        Full pipeline: question -> SQL -> (optional execution).
        
        Args:
            question: Natural language question
            database: Database to query
            execute: Whether to execute the generated SQL
            max_rows: Maximum rows to return
            
        Returns:
            SQLResult with generated SQL and optional results
        """
        # Generate SQL
        sql_query = await self.generate_sql(question, database)
        
        if sql_query.query_type == "ERROR":
            return SQLResult(
                query=sql_query,
                error=sql_query.explanation,
                success=False
            )
        
        # Get explanation
        sql_query.explanation = await self.explain_sql(sql_query.sql, database)
        
        # Execute if requested
        if execute:
            result = await self.execute(sql_query.sql, database, max_rows)
            result.query = sql_query
            return result
        
        return SQLResult(
            query=sql_query,
            success=True
        )

    def get_schema(self, database: Optional[str] = None) -> Optional[DatabaseSchema]:
        """Get schema for a database"""
        db_name = database or self.default_database
        return self.schemas.get(db_name)

    def list_databases(self) -> List[str]:
        """List all registered databases"""
        return list(self.schemas.keys())

    def list_tables(self, database: Optional[str] = None) -> List[str]:
        """List tables in a database"""
        schema = self.get_schema(database)
        if schema:
            return [t.name for t in schema.tables]
        return []


# Singleton instance
sql_agent = SQLAgent()

