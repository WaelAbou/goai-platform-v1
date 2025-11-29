"""
File Upload API - Page-Aware Document Ingestion

Endpoints for uploading and processing documents with page tracking.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
import hashlib
from datetime import datetime

from modules.ingestion.file_parser import file_parser, ParsedDocument
from modules.rag import rag_engine


router = APIRouter()


class UploadResponse(BaseModel):
    """Response after successful file upload."""
    document_id: str
    filename: str
    file_type: str
    total_pages: int
    chunks_created: int
    status: str
    message: str


class PageInfo(BaseModel):
    """Information about a document page."""
    page_number: int
    char_count: int
    preview: str


class DocumentInfo(BaseModel):
    """Detailed document information."""
    document_id: str
    filename: str
    file_type: str
    total_pages: int
    pages: List[PageInfo]
    metadata: dict


@router.post("/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    chunk_size: int = Form(default=1000),
    chunk_overlap: int = Form(default=200),
    preserve_pages: bool = Form(default=True)
):
    """
    Upload and ingest a document file with page awareness.
    
    Supported formats:
    - PDF (.pdf) - Extracts text page by page
    - Word (.docx) - Extracts with page estimation
    - Text (.txt, .md) - Splits into estimated pages
    - Excel (.xlsx) - Each sheet becomes a page
    
    Args:
        file: The file to upload
        chunk_size: Size of text chunks (default: 1000)
        chunk_overlap: Overlap between chunks (default: 200)
        preserve_pages: Keep chunks within page boundaries (default: True)
    
    Returns:
        Upload result with document ID and chunk count
    """
    # Validate file type
    file_type = file_parser.get_file_type(file.filename)
    if file_type is None:
        supported = ", ".join(file_parser.get_supported_extensions())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {supported}"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")
        
        # Parse document with page tracking
        parsed_doc = file_parser.parse(content, file.filename)
        
        # Ingest each page as chunks with page metadata
        total_chunks = 0
        
        for page in parsed_doc.pages:
            if not page.content.strip():
                continue
            
            # Add page metadata
            page_metadata = {
                "document_id": parsed_doc.document_id,
                "filename": parsed_doc.filename,
                "file_type": parsed_doc.file_type,
                "page": page.page_number,
                "total_pages": parsed_doc.total_pages,
                **page.metadata
            }
            
            if preserve_pages:
                # Chunk within page boundaries
                chunks = _chunk_text(
                    page.content, 
                    chunk_size, 
                    chunk_overlap
                )
                
                for i, chunk in enumerate(chunks):
                    chunk_meta = {
                        **page_metadata,
                        "chunk_index": i,
                        "chunks_in_page": len(chunks)
                    }
                    
                    await rag_engine.ingest_document(
                        content=chunk,
                        filename=f"{parsed_doc.filename}_p{page.page_number}_c{i}",
                        metadata=chunk_meta
                    )
                    total_chunks += 1
            else:
                # Ingest whole page as one chunk
                await rag_engine.ingest_document(
                    content=page.content,
                    filename=f"{parsed_doc.filename}_p{page.page_number}",
                    metadata=page_metadata
                )
                total_chunks += 1
        
        return UploadResponse(
            document_id=parsed_doc.document_id,
            filename=parsed_doc.filename,
            file_type=file_type,
            total_pages=parsed_doc.total_pages,
            chunks_created=total_chunks,
            status="success",
            message=f"Successfully processed {parsed_doc.total_pages} pages into {total_chunks} chunks"
        )
        
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Missing dependency: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {str(e)}"
        )


@router.post("/files", response_model=List[UploadResponse])
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    chunk_size: int = Form(default=1000),
    chunk_overlap: int = Form(default=200)
):
    """
    Upload multiple files at once.
    
    Returns list of upload results for each file.
    """
    results = []
    
    for file in files:
        try:
            # Read file content
            content = await file.read()
            
            if len(content) == 0:
                results.append(UploadResponse(
                    document_id="",
                    filename=file.filename,
                    file_type="unknown",
                    total_pages=0,
                    chunks_created=0,
                    status="error",
                    message="Empty file"
                ))
                continue
            
            # Parse document
            parsed_doc = file_parser.parse(content, file.filename)
            
            # Ingest pages
            total_chunks = 0
            for page in parsed_doc.pages:
                if not page.content.strip():
                    continue
                
                page_metadata = {
                    "document_id": parsed_doc.document_id,
                    "filename": parsed_doc.filename,
                    "file_type": parsed_doc.file_type,
                    "page": page.page_number,
                    "total_pages": parsed_doc.total_pages,
                    **page.metadata
                }
                
                chunks = _chunk_text(page.content, chunk_size, chunk_overlap)
                
                for i, chunk in enumerate(chunks):
                    chunk_meta = {**page_metadata, "chunk_index": i}
                    await rag_engine.ingest_document(
                        content=chunk,
                        filename=f"{parsed_doc.filename}_p{page.page_number}_c{i}",
                        metadata=chunk_meta
                    )
                    total_chunks += 1
            
            results.append(UploadResponse(
                document_id=parsed_doc.document_id,
                filename=parsed_doc.filename,
                file_type=parsed_doc.file_type,
                total_pages=parsed_doc.total_pages,
                chunks_created=total_chunks,
                status="success",
                message=f"Processed {parsed_doc.total_pages} pages"
            ))
            
        except Exception as e:
            results.append(UploadResponse(
                document_id="",
                filename=file.filename,
                file_type="unknown",
                total_pages=0,
                chunks_created=0,
                status="error",
                message=str(e)
            ))
    
    return results


@router.get("/supported-types")
async def get_supported_types():
    """Get list of supported file types."""
    return {
        "extensions": file_parser.get_supported_extensions(),
        "types": {
            "pdf": {
                "extensions": [".pdf"],
                "description": "PDF documents with page-accurate extraction"
            },
            "docx": {
                "extensions": [".docx", ".doc"],
                "description": "Word documents with estimated pages"
            },
            "text": {
                "extensions": [".txt", ".md", ".markdown"],
                "description": "Plain text and Markdown files"
            },
            "excel": {
                "extensions": [".xlsx", ".xls"],
                "description": "Excel files (each sheet = 1 page)"
            },
            "csv": {
                "extensions": [".csv"],
                "description": "CSV data files"
            }
        }
    }


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end near chunk boundary
            for sep in ['. ', '! ', '? ', '\n\n', '\n', ' ']:
                last_sep = text[start:end].rfind(sep)
                if last_sep > chunk_size * 0.5:  # At least half the chunk
                    end = start + last_sep + len(sep)
                    break
        
        chunks.append(text[start:end].strip())
        start = end - overlap
    
    return [c for c in chunks if c]  # Remove empty chunks

