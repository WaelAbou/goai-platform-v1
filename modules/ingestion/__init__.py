# Ingestion Module
from .engine import (
    IngestionEngine,
    ingestion_engine,
    TextExtractor,
    TextChunker,
    ChunkConfig,
    ChunkingStrategy,
    DocumentChunk,
    IngestedDocument,
    FileType
)
from .ocr import (
    OCREngine,
    ocr_engine,
    OCRProvider,
    DocumentType as OCRDocumentType,
    OCRResult,
)

__all__ = [
    "IngestionEngine",
    "ingestion_engine",
    "TextExtractor",
    "TextChunker",
    "ChunkConfig",
    "ChunkingStrategy",
    "DocumentChunk",
    "IngestedDocument",
    "FileType",
    # OCR exports
    "OCREngine",
    "ocr_engine",
    "OCRProvider",
    "OCRDocumentType",
    "OCRResult",
]
