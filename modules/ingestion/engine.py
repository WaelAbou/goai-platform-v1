"""
Ingestion Engine - Document processing, chunking, and embedding pipeline.
Supports multiple file formats and chunking strategies.
"""

import os
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio


class FileType(Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    UNKNOWN = "unknown"


class ChunkingStrategy(Enum):
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"


@dataclass
class ChunkConfig:
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 1000  # characters
    chunk_overlap: int = 200
    min_chunk_size: int = 100
    separators: List[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " ", ""])


@dataclass
class DocumentChunk:
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0


@dataclass
class IngestedDocument:
    id: str
    filename: str
    file_type: FileType
    chunks: List[DocumentChunk] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_content: str = ""
    total_chunks: int = 0
    status: str = "pending"
    error: Optional[str] = None


class TextExtractor:
    """Extract text from various file formats"""

    @staticmethod
    def detect_file_type(filename: str, content: Optional[bytes] = None) -> FileType:
        """Detect file type from extension or content"""
        ext = Path(filename).suffix.lower()
        
        type_map = {
            ".txt": FileType.TEXT,
            ".md": FileType.MARKDOWN,
            ".markdown": FileType.MARKDOWN,
            ".pdf": FileType.PDF,
            ".html": FileType.HTML,
            ".htm": FileType.HTML,
            ".json": FileType.JSON,
            ".csv": FileType.CSV,
        }
        
        return type_map.get(ext, FileType.UNKNOWN)

    @staticmethod
    async def extract_text(content: bytes, file_type: FileType) -> str:
        """Extract text content from file bytes"""
        
        if file_type == FileType.TEXT or file_type == FileType.MARKDOWN:
            return content.decode("utf-8", errors="ignore")
        
        elif file_type == FileType.HTML:
            # Simple HTML text extraction
            text = content.decode("utf-8", errors="ignore")
            # Remove script and style elements
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        
        elif file_type == FileType.JSON:
            import json
            data = json.loads(content.decode("utf-8"))
            # Convert JSON to readable text
            return json.dumps(data, indent=2)
        
        elif file_type == FileType.CSV:
            text = content.decode("utf-8", errors="ignore")
            # Convert CSV to readable format
            lines = text.strip().split("\n")
            if lines:
                headers = lines[0].split(",")
                rows = [line.split(",") for line in lines[1:]]
                formatted = []
                for row in rows:
                    row_text = ", ".join(f"{h}: {v}" for h, v in zip(headers, row) if v)
                    formatted.append(row_text)
                return "\n".join(formatted)
            return text
        
        elif file_type == FileType.PDF:
            # PDF extraction would require pypdf or similar
            # For now, return placeholder
            return "[PDF content extraction requires pypdf library]"
        
        return content.decode("utf-8", errors="ignore")


class TextChunker:
    """Split text into chunks using various strategies"""

    def __init__(self, config: ChunkConfig):
        self.config = config

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """Split text into chunks based on configured strategy"""
        
        if self.config.strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(text, metadata)
        elif self.config.strategy == ChunkingStrategy.SENTENCE:
            return self._chunk_by_sentence(text, metadata)
        elif self.config.strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraph(text, metadata)
        elif self.config.strategy == ChunkingStrategy.RECURSIVE:
            return self._chunk_recursive(text, metadata)
        else:
            return self._chunk_fixed_size(text, metadata)

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_char: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentChunk:
        """Create a document chunk with ID"""
        chunk_id = hashlib.md5(f"{content[:50]}_{index}".encode()).hexdigest()
        return DocumentChunk(
            id=chunk_id,
            content=content,
            metadata=metadata or {},
            chunk_index=index,
            start_char=start_char,
            end_char=start_char + len(content)
        )

    def _chunk_fixed_size(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """Split text into fixed-size chunks with overlap"""
        chunks = []
        start = 0
        index = 0
        
        while start < len(text):
            end = start + self.config.chunk_size
            chunk_text = text[start:end]
            
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(self._create_chunk(chunk_text, index, start, metadata))
                index += 1
            
            start = end - self.config.chunk_overlap
        
        return chunks

    def _chunk_by_sentence(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """Split text by sentences, respecting chunk size limits"""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        start_char = 0
        index = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.config.chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk.strip(), index, start_char, metadata))
                    index += 1
                    start_char += len(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunks.append(self._create_chunk(current_chunk.strip(), index, start_char, metadata))
        
        return chunks

    def _chunk_by_paragraph(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """Split text by paragraphs"""
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = ""
        start_char = 0
        index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) > self.config.chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, index, start_char, metadata))
                    index += 1
                    start_char += len(current_chunk) + 2  # +2 for \n\n
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunks.append(self._create_chunk(current_chunk, index, start_char, metadata))
        
        return chunks

    def _chunk_recursive(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """Recursively split text using multiple separators"""
        return self._recursive_split(text, self.config.separators, 0, metadata or {})

    def _recursive_split(
        self,
        text: str,
        separators: List[str],
        char_offset: int,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Recursively split text, trying separators in order"""
        
        if len(text) <= self.config.chunk_size:
            if len(text) >= self.config.min_chunk_size:
                return [self._create_chunk(text, 0, char_offset, metadata)]
            return []
        
        if not separators:
            # Fall back to fixed size
            return self._chunk_fixed_size(text, metadata)
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        if separator and separator in text:
            parts = text.split(separator)
        else:
            # Try next separator
            return self._recursive_split(text, remaining_separators, char_offset, metadata)
        
        chunks = []
        current_chunk = ""
        current_offset = char_offset
        index = len(chunks)
        
        for i, part in enumerate(parts):
            part_with_sep = part + (separator if i < len(parts) - 1 else "")
            
            if len(current_chunk) + len(part_with_sep) > self.config.chunk_size:
                if current_chunk:
                    # Recursively split if still too large
                    if len(current_chunk) > self.config.chunk_size:
                        sub_chunks = self._recursive_split(
                            current_chunk, remaining_separators, current_offset, metadata
                        )
                        for sc in sub_chunks:
                            sc.chunk_index = index
                            index += 1
                        chunks.extend(sub_chunks)
                    else:
                        chunk = self._create_chunk(current_chunk, index, current_offset, metadata)
                        chunks.append(chunk)
                        index += 1
                    current_offset += len(current_chunk)
                current_chunk = part_with_sep
            else:
                current_chunk += part_with_sep
        
        if current_chunk:
            if len(current_chunk) > self.config.chunk_size:
                sub_chunks = self._recursive_split(
                    current_chunk, remaining_separators, current_offset, metadata
                )
                for sc in sub_chunks:
                    sc.chunk_index = index
                    index += 1
                chunks.extend(sub_chunks)
            elif len(current_chunk) >= self.config.min_chunk_size:
                chunks.append(self._create_chunk(current_chunk, index, current_offset, metadata))
        
        return chunks


class IngestionEngine:
    """
    Main ingestion engine for processing documents.
    Handles extraction, chunking, and embedding.
    """

    def __init__(self, chunk_config: Optional[ChunkConfig] = None):
        self.chunk_config = chunk_config or ChunkConfig()
        self.extractor = TextExtractor()
        self.chunker = TextChunker(self.chunk_config)
        self.vector_retriever = None
        self.embedding_provider = None

    def set_vector_retriever(self, retriever):
        """Set the vector retriever for storing embeddings"""
        self.vector_retriever = retriever

    def set_embedding_provider(self, provider):
        """Set the embedding provider"""
        self.embedding_provider = provider

    async def ingest_text(
        self,
        text: str,
        filename: str = "text_input",
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestedDocument:
        """
        Ingest raw text content.
        
        Args:
            text: The text content to ingest
            filename: Optional filename for identification
            metadata: Optional metadata to attach
            
        Returns:
            IngestedDocument with chunks
        """
        doc_id = hashlib.md5(f"{filename}_{text[:100]}".encode()).hexdigest()
        metadata = metadata or {}
        metadata["source"] = filename
        
        try:
            # Chunk the text
            chunks = self.chunker.chunk(text, metadata)
            
            # Generate embeddings if provider is set
            if self.embedding_provider and chunks:
                chunk_texts = [c.content for c in chunks]
                embeddings = await self.embedding_provider.embed(chunk_texts)
                for chunk, embedding in zip(chunks, embeddings):
                    chunk.embedding = embedding
            
            # Store in vector retriever if available
            if self.vector_retriever and chunks:
                await self.vector_retriever.add_documents(
                    documents=[c.content for c in chunks],
                    embeddings=[c.embedding for c in chunks] if chunks[0].embedding else None,
                    ids=[c.id for c in chunks],
                    metadata=[{**c.metadata, "doc_id": doc_id, "chunk_index": c.chunk_index} for c in chunks]
                )
            
            return IngestedDocument(
                id=doc_id,
                filename=filename,
                file_type=FileType.TEXT,
                chunks=chunks,
                metadata=metadata,
                raw_content=text,
                total_chunks=len(chunks),
                status="completed"
            )
        
        except Exception as e:
            return IngestedDocument(
                id=doc_id,
                filename=filename,
                file_type=FileType.TEXT,
                metadata=metadata,
                raw_content=text,
                status="failed",
                error=str(e)
            )

    async def ingest_file(
        self,
        content: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestedDocument:
        """
        Ingest a file from bytes.
        
        Args:
            content: File content as bytes
            filename: Original filename
            metadata: Optional metadata
            
        Returns:
            IngestedDocument with chunks
        """
        doc_id = hashlib.md5(f"{filename}_{len(content)}".encode()).hexdigest()
        metadata = metadata or {}
        metadata["source"] = filename
        metadata["size_bytes"] = len(content)
        
        try:
            # Detect file type
            file_type = TextExtractor.detect_file_type(filename, content)
            metadata["file_type"] = file_type.value
            
            # Extract text
            text = await TextExtractor.extract_text(content, file_type)
            
            # Chunk the text
            chunks = self.chunker.chunk(text, metadata)
            
            # Generate embeddings if provider is set
            if self.embedding_provider and chunks:
                chunk_texts = [c.content for c in chunks]
                embeddings = await self.embedding_provider.embed(chunk_texts)
                for chunk, embedding in zip(chunks, embeddings):
                    chunk.embedding = embedding
            
            # Store in vector retriever if available
            if self.vector_retriever and chunks:
                await self.vector_retriever.add_documents(
                    documents=[c.content for c in chunks],
                    embeddings=[c.embedding for c in chunks] if chunks[0].embedding else None,
                    ids=[c.id for c in chunks],
                    metadata=[{**c.metadata, "doc_id": doc_id, "chunk_index": c.chunk_index} for c in chunks]
                )
            
            return IngestedDocument(
                id=doc_id,
                filename=filename,
                file_type=file_type,
                chunks=chunks,
                metadata=metadata,
                raw_content=text,
                total_chunks=len(chunks),
                status="completed"
            )
        
        except Exception as e:
            return IngestedDocument(
                id=doc_id,
                filename=filename,
                file_type=FileType.UNKNOWN,
                metadata=metadata,
                status="failed",
                error=str(e)
            )

    async def ingest_batch(
        self,
        items: List[Tuple[bytes, str, Optional[Dict[str, Any]]]]
    ) -> List[IngestedDocument]:
        """
        Ingest multiple files in batch.
        
        Args:
            items: List of (content, filename, metadata) tuples
            
        Returns:
            List of IngestedDocument objects
        """
        tasks = [
            self.ingest_file(content, filename, metadata)
            for content, filename, metadata in items
        ]
        return await asyncio.gather(*tasks)


# Singleton instance
ingestion_engine = IngestionEngine()

