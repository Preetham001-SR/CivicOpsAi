import uuid
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import structlog

from app.rag.retrieval import RetrievalResult

logger = structlog.get_logger()


@dataclass
class RerankConfig:
    top_k: int = 10
    diversity_penalty: float = 0.1
    category_boost: float = 0.2
    source_priority: Dict[str, float] = None
    
    def __post_init__(self):
        if self.source_priority is None:
            self.source_priority = {
                "municipal_code": 1.2,
                "policy_document": 1.1,
                "regulation": 1.1,
                "past_incident": 1.0,
                "guideline": 0.9,
            }


class Reranker:
    def __init__(self, config: Optional[RerankConfig] = None):
        self.config = config or RerankConfig()

    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        config: Optional[RerankConfig] = None,
    ) -> List[RetrievalResult]:
        cfg = config or self.config
        
        if not results:
            return []
        
        scored_results = []
        for result in results:
            score = result.similarity_score
            
            source_boost = cfg.source_priority.get(result.document.source, 1.0)
            score *= source_boost
            
            if cfg.category_boost > 0 and result.document.category:
                query_lower = query.lower()
                category_str = result.document.category.value if hasattr(result.document.category, 'value') else str(result.document.category)
                if category_str in query_lower:
                    score *= (1 + cfg.category_boost)
            
            scored_results.append((score, result))
        
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        final_results = []
        seen_content = set()
        
        for score, result in scored_results:
            content_sig = result.document.content[:200].lower().strip()
            if content_sig in seen_content:
                score *= (1 - cfg.diversity_penalty)
            else:
                seen_content.add(content_sig)
            
            new_result = RetrievalResult(
                document=result.document,
                similarity_score=score,
                rank=len(final_results) + 1,
            )
            final_results.append(new_result)
            
            if len(final_results) >= cfg.top_k:
                break
        
        logger.info(
            "reranking_completed",
            input_count=len(results),
            output_count=len(final_results),
        )
        
        return final_results


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name, device="cpu")
            except Exception as e:
                logger.error("cross_encoder_load_failed", model=self.model_name, error=str(e))
                raise

    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int = 10,
    ) -> List[RetrievalResult]:
        if not results:
            return []
        
        try:
            self._load_model()
            
            pairs = [(query, result.document.content) for result in results]
            scores = self._model.predict(pairs)
            
            scored_results = list(zip(scores, results))
            scored_results.sort(key=lambda x: x[0], reverse=True)
            
            final_results = []
            for i, (score, result) in enumerate(scored_results[:top_k]):
                final_results.append(RetrievalResult(
                    document=result.document,
                    similarity_score=float(score),
                    rank=i + 1,
                ))
            
            return final_results
            
        except Exception as e:
            logger.error("cross_encoder_rerank_failed", error=str(e))
            return results[:top_k]


def combine_and_rerank(
    rules: List[RetrievalResult],
    incidents: List[RetrievalResult],
    query: str,
    config: Optional[RerankConfig] = None,
) -> Tuple[List[RetrievalResult], List[RetrievalResult]]:
    reranker = Reranker(config)
    
    reranked_rules = reranker.rerank(query, rules, config)
    reranked_incidents = reranker.rerank(query, incidents, config)
    
    return reranked_rules, reranked_incidents