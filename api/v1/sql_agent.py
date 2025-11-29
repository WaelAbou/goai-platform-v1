from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any, Dict

from modules.sql_agent import sql_agent, DatabaseSchema, TableSchema, DatabaseType
from core.llm import llm_router

router = APIRouter()

# Wire up the SQL agent with the LLM router
sql_agent.set_llm_router(llm_router)


class SQLQueryRequest(BaseModel):
    question: str
    database: Optional[str] = None
    execute: Optional[bool] = False
    max_rows: Optional[int] = 100


class SQLQueryResponse(BaseModel):
    sql: str
    explanation: str
    tables_used: List[str] = []
    query_type: str = ""
    results: List[Dict[str, Any]] = []
    row_count: int = 0
    success: bool = True
    error: Optional[str] = None


class ExplainRequest(BaseModel):
    sql: str
    database: Optional[str] = None


class SchemaRegistration(BaseModel):
    name: str
    type: str = "sqlite"  # sqlite, postgresql, mysql
    tables: Dict[str, Dict[str, Any]]


@router.post("/query", response_model=SQLQueryResponse)
async def sql_query(request: SQLQueryRequest):
    """
    Convert natural language question to SQL and optionally execute.
    """
    result = await sql_agent.query(
        question=request.question,
        database=request.database,
        execute=request.execute,
        max_rows=request.max_rows
    )
    
    return SQLQueryResponse(
        sql=result.query.sql,
        explanation=result.query.explanation,
        tables_used=result.query.tables_used,
        query_type=result.query.query_type,
        results=result.data,
        row_count=result.row_count,
        success=result.success,
        error=result.error
    )


@router.post("/generate")
async def generate_sql(request: SQLQueryRequest):
    """
    Generate SQL from natural language without executing.
    """
    query = await sql_agent.generate_sql(
        question=request.question,
        database=request.database
    )
    
    return {
        "sql": query.sql,
        "tables_used": query.tables_used,
        "query_type": query.query_type
    }


@router.post("/explain")
async def explain_query(request: ExplainRequest):
    """
    Explain a SQL query in natural language.
    """
    explanation = await sql_agent.explain_sql(
        sql=request.sql,
        database=request.database
    )
    
    return {
        "sql": request.sql,
        "explanation": explanation
    }


@router.post("/schema/register")
async def register_schema(schema: SchemaRegistration):
    """
    Register a database schema for SQL generation.
    """
    try:
        tables = []
        for table_name, table_info in schema.tables.items():
            tables.append(TableSchema(
                name=table_name,
                columns=table_info.get("columns", []),
                primary_key=table_info.get("primary_key"),
                foreign_keys=table_info.get("foreign_keys", []),
                sample_data=table_info.get("sample_data", [])
            ))
        
        db_schema = DatabaseSchema(
            name=schema.name,
            db_type=DatabaseType(schema.type),
            tables=tables
        )
        
        sql_agent.register_schema(db_schema)
        
        return {
            "status": "registered",
            "database": schema.name,
            "tables": [t.name for t in tables]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schema/{database}")
async def get_schema(database: str):
    """
    Get the schema of a registered database.
    """
    schema = sql_agent.get_schema(database)
    
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Database '{database}' not found")
    
    return {
        "database": schema.name,
        "type": schema.db_type.value,
        "tables": [
            {
                "name": t.name,
                "columns": t.columns,
                "primary_key": t.primary_key,
                "foreign_keys": t.foreign_keys
            }
            for t in schema.tables
        ]
    }


@router.get("/databases")
async def list_databases():
    """
    List all registered databases.
    """
    return {
        "databases": sql_agent.list_databases(),
        "default": sql_agent.default_database
    }


@router.get("/tables/{database}")
async def list_tables(database: str):
    """
    List tables in a database.
    """
    tables = sql_agent.list_tables(database)
    
    if not tables:
        raise HTTPException(status_code=404, detail=f"Database '{database}' not found or has no tables")
    
    return {
        "database": database,
        "tables": tables
    }
