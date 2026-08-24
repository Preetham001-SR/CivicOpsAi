import uuid
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import structlog

from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RagDocument, ComplaintCategory

logger = structlog.get_logger()


@dataclass
class RetrievalResult:
    document: RagDocument
    similarity_score: float
    rank: int


@dataclass
class RetrievalConfig:
    top_k: int = 20
    similarity_threshold: float = 0.5
    category_filter: Optional[ComplaintCategory] = None
    source_filter: Optional[str] = None


def _embedding_to_vector_str(embedding: List[float]) -> str:
    """Convert embedding list to pgvector string format for asyncpg."""
    return '[' + ','.join(str(x) for x in embedding) + ']'


class Retriever:
    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        config: Optional[RetrievalConfig] = None,
    ):
        self.config = config or RetrievalConfig()
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    async def retrieve(
        self,
        query: str,
        db: AsyncSession,
        config: Optional[RetrievalConfig] = None,
    ) -> List[RetrievalResult]:
        cfg = config or self.config

        query_embedding = self.embeddings.embed_query(query)
        query_vector_str = _embedding_to_vector_str(query_embedding)

        # Build SQL with proper parameter placeholders
        param_idx = 1
        sql_parts = [
            "SELECT",
            "    id, title, content, embedding, metadata, source, category, created_at,",
            "    1 - (embedding::vector <=> $" + str(param_idx) + "::vector) AS similarity",
            "FROM rag_documents",
            "WHERE 1 - (embedding::vector <=> $" + str(param_idx) + "::vector) >= $" + str(param_idx + 1),
        ]
        param_idx += 2
        params = [query_vector_str, cfg.similarity_threshold]

        if cfg.category_filter:
            sql_parts.append("AND category = $" + str(param_idx))
            params.append(cfg.category_filter.value)
            param_idx += 1

        if cfg.source_filter:
            sql_parts.append("AND source = $" + str(param_idx))
            params.append(cfg.source_filter)
            param_idx += 1

        sql_parts.append("ORDER BY similarity DESC LIMIT $" + str(param_idx))
        params.append(cfg.top_k)

        sql = " ".join(sql_parts)

        # Use asyncpg directly for vector queries
        import asyncpg
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="civicops",
            password="civicops",
            database="civicops",
        )

        try:
            rows = await conn.fetch(sql, *params)

            results = []
            for rank, row in enumerate(rows, 1):
                doc = RagDocument(
                    id=row['id'],
                    title=row['title'],
                    content=row['content'],
                    embedding=row['embedding'],
                    doc_metadata=row['metadata'],
                    source=row['source'],
                    category=row['category'],
                    created_at=row['created_at'],
                )
                results.append(RetrievalResult(
                    document=doc,
                    similarity_score=float(row['similarity']),
                    rank=rank,
                ))

            logger.info(
                "retrieval_completed",
                query=query[:100],
                results_count=len(results),
                threshold=cfg.similarity_threshold,
            )

            return results
        finally:
            await conn.close()

    async def retrieve_by_category(
        self,
        query: str,
        category: ComplaintCategory,
        db: AsyncSession,
        top_k: int = 10,
    ) -> List[RetrievalResult]:
        config = RetrievalConfig(
            top_k=top_k,
            category_filter=category,
        )
        return await self.retrieve(query, db, config)

    async def retrieve_rules(
        self,
        query: str,
        db: AsyncSession,
        top_k: int = 10,
    ) -> List[RetrievalResult]:
        config = RetrievalConfig(
            top_k=top_k,
            source_filter="municipal_code",
        )
        return await self.retrieve(query, db, config)

    async def retrieve_incidents(
        self,
        query: str,
        db: AsyncSession,
        top_k: int = 10,
    ) -> List[RetrievalResult]:
        config = RetrievalConfig(
            top_k=top_k,
            source_filter="past_incident",
        )
        return await self.retrieve(query, db, config)

    async def hybrid_retrieve(
        self,
        query: str,
        db: AsyncSession,
        category: Optional[ComplaintCategory] = None,
        rules_top_k: int = 5,
        incidents_top_k: int = 5,
    ) -> Tuple[List[RetrievalResult], List[RetrievalResult]]:
        rules_config = RetrievalConfig(
            top_k=rules_top_k,
            category_filter=category,
            source_filter="municipal_code",
        )
        incidents_config = RetrievalConfig(
            top_k=incidents_top_k,
            category_filter=category,
            source_filter="past_incident",
        )

        rules = await self.retrieve(query, db, rules_config)
        incidents = await self.retrieve(query, db, incidents_config)

        return rules, incidents


async def get_retriever(
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> Retriever:
    return Retriever(embedding_model=embedding_model)