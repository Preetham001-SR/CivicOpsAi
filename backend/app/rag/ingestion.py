import uuid
import hashlib
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import structlog
import asyncpg

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document as LangChainDocument

from app.db.models import RagDocument, ComplaintCategory
from app.db.session import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = structlog.get_logger()


@dataclass
class ChunkConfig:
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 100


@dataclass
class IngestionResult:
    document_id: uuid.UUID
    title: str
    chunks_created: int
    source: str
    category: Optional[ComplaintCategory]


class DocumentIngestor:
    def __init__(
        self,
        config: Optional[ChunkConfig] = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.config = config or ChunkConfig()
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
        )

    def _generate_chunk_id(self, doc_id: uuid.UUID, chunk_index: int, content: str) -> str:
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{doc_id}-{chunk_index}-{content_hash}"

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[LangChainDocument]:
        chunks = self.text_splitter.split_text(text)
        
        documents = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < self.config.min_chunk_size:
                continue
            
            chunk_metadata = metadata.copy()
            doc_id = metadata.get("document_id")
            if isinstance(doc_id, uuid.UUID):
                doc_id = str(doc_id)
            elif doc_id is None:
                doc_id = str(uuid.uuid4())
            
            chunk_metadata.update({
                "chunk_index": i,
                "chunk_id": self._generate_chunk_id(doc_id, i, chunk),
            })
            documents.append(LangChainDocument(page_content=chunk, metadata=chunk_metadata))
        
        return documents

    async def ingest_file(
        self,
        file_path: Path,
        title: str,
        source: str,
        category: Optional[ComplaintCategory] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IngestionResult:
        content = file_path.read_text(encoding="utf-8")
        return await self.ingest_text(
            content=content,
            title=title,
            source=source,
            category=category,
            metadata=metadata,
        )

    async def ingest_text(
        self,
        content: str,
        title: str,
        source: str,
        category: Optional[ComplaintCategory] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IngestionResult:
        doc_id = uuid.uuid4()
        
        base_metadata = {
            "document_id": str(doc_id),
            "title": title,
            "source": source,
            "category": category.value if category else None,
        }
        if metadata:
            clean_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, uuid.UUID):
                    clean_metadata[k] = str(v)
                else:
                    clean_metadata[k] = v
            base_metadata.update(clean_metadata)
        
        chunks = self.chunk_text(content, base_metadata)
        
        if not chunks:
            logger.warning("no_chunks_created", title=title, source=source)
            return IngestionResult(
                document_id=doc_id,
                title=title,
                chunks_created=0,
                source=source,
                category=category,
            )
        
        chunk_texts = [chunk.page_content for chunk in chunks]
        embeddings = self.embeddings.embed_documents(chunk_texts)
        
        # Use asyncpg directly for bulk insert to avoid SQLAlchemy type issues
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="civicops",
            password="civicops",
            database="civicops",
        )
        
        try:
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = doc_id if i == 0 else uuid.uuid4()
                chunk_title = f"{title} (chunk {i+1}/{len(chunks)})" if len(chunks) > 1 else title
                
                await conn.execute(
                    """INSERT INTO rag_documents (id, title, content, embedding, metadata, source, category, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())""",
                    chunk_id,
                    chunk_title,
                    chunk.page_content,
                    embedding,
                    json.dumps(chunk.metadata),
                    source,
                    category.value if category else None,
                )
            
            logger.info(
                "document_ingested",
                document_id=str(doc_id),
                title=title,
                source=source,
                category=category.value if category else None,
                chunks_created=len(chunks),
            )
            
            return IngestionResult(
                document_id=doc_id,
                title=title,
                chunks_created=len(chunks),
                source=source,
                category=category,
            )
        finally:
            await conn.close()

    async def ingest_directory(
        self,
        directory: Path,
        source: str,
        category_map: Optional[Dict[str, ComplaintCategory]] = None,
        file_pattern: str = "*.txt",
    ) -> List[IngestionResult]:
        results = []
        
        for file_path in directory.glob(file_pattern):
            category = None
            if category_map:
                for pattern, cat in category_map.items():
                    if pattern.lower() in file_path.name.lower():
                        category = cat
                        break
            
            try:
                result = await self.ingest_file(
                    file_path=file_path,
                    title=file_path.stem,
                    source=source,
                    category=category,
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "ingest_file_failed",
                    file=str(file_path),
                    error=str(e),
                )
        
        return results


async def get_document_by_id(doc_id: uuid.UUID) -> Optional[RagDocument]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RagDocument).where(RagDocument.id == doc_id))
        return result.scalar_one_or_none()


async def delete_document(doc_id: uuid.UUID) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RagDocument).where(RagDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc:
            await db.delete(doc)
            await db.commit()
            return True
        return False