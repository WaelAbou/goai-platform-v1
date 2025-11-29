from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List
from pydantic import BaseModel

from modules.ingestion import ingestion_engine, ChunkConfig, ChunkingStrategy

router = APIRouter()


class IngestTextRequest(BaseModel):
    content: str
    filename: Optional[str] = "text_input"
    chunk_size: Optional[int] = 1000
    chunk_overlap: Optional[int] = 200
    metadata: Optional[dict] = None


class IngestResponse(BaseModel):
    id: str
    filename: str
    total_chunks: int
    status: str
    error: Optional[str] = None


@router.post("/", response_model=IngestResponse)
async def ingest_document(
    file: Optional[UploadFile] = File(None),
    content: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200)
):
    """
    Ingest a document into the platform.
    Accepts either a file upload or raw text content.
    """
    # Configure chunking
    ingestion_engine.chunk_config = ChunkConfig(
        strategy=ChunkingStrategy.RECURSIVE,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    if file:
        # Handle file upload
        file_content = await file.read()
        result = await ingestion_engine.ingest_file(
            content=file_content,
            filename=file.filename or filename or "uploaded_file",
            metadata={"source": "upload"}
        )
    elif content:
        # Handle text content
        result = await ingestion_engine.ingest_text(
            text=content,
            filename=filename or "text_input",
            metadata={"source": "text_input"}
        )
    else:
        raise HTTPException(status_code=400, detail="Either file or content must be provided")
    
    return IngestResponse(
        id=result.id,
        filename=result.filename,
        total_chunks=result.total_chunks,
        status=result.status,
        error=result.error
    )


@router.post("/text", response_model=IngestResponse)
async def ingest_text(request: IngestTextRequest):
    """
    Ingest raw text content.
    """
    ingestion_engine.chunk_config = ChunkConfig(
        strategy=ChunkingStrategy.RECURSIVE,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap
    )
    
    result = await ingestion_engine.ingest_text(
        text=request.content,
        filename=request.filename,
        metadata=request.metadata
    )
    
    return IngestResponse(
        id=result.id,
        filename=result.filename,
        total_chunks=result.total_chunks,
        status=result.status,
        error=result.error
    )


@router.post("/batch")
async def ingest_batch(files: List[UploadFile] = File(...)):
    """Batch ingest multiple documents"""
    items = []
    for file in files:
        content = await file.read()
        items.append((content, file.filename, {"source": "batch_upload"}))
    
    results = await ingestion_engine.ingest_batch(items)
    
    return {
        "ingested": len([r for r in results if r.status == "completed"]),
        "failed": len([r for r in results if r.status == "failed"]),
        "results": [
            {
                "id": r.id,
                "filename": r.filename,
                "status": r.status,
                "chunks": r.total_chunks,
                "error": r.error
            }
            for r in results
        ]
    }


@router.get("/status/{doc_id}")
async def get_ingest_status(doc_id: str):
    """Get status of an ingestion job"""
    # In a full implementation, this would query a job queue
    return {
        "doc_id": doc_id,
        "status": "completed",
        "message": "Document ingestion tracking requires persistent storage"
    }
