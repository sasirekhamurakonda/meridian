import asyncio
from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding

from app.config import get_settings
from app.models.schemas import Passage

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache
def _get_model() -> TextEmbedding:
    return TextEmbedding(model_name=MODEL_NAME)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _embed_texts(texts: list[str], batch_size: int) -> list[np.ndarray]:
    model = _get_model()
    vectors: list[np.ndarray] = []
    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        vectors.extend(np.array(vec) for vec in model.embed(chunk))
    return vectors


def _dedupe_passages(passages: list[Passage]) -> list[Passage]:
    seen: set[str] = set()
    unique: list[Passage] = []
    for passage in passages:
        key = passage.url or passage.text[:200]
        if key in seen:
            continue
        seen.add(key)
        unique.append(passage)
    return unique


class EmbeddingService:
    async def rank(self, query: str, passages: list[Passage], top_k: int | None = None) -> list[Passage]:
        settings = get_settings()
        k = top_k or settings.top_k_passages
        deduped = _dedupe_passages(passages)
        if not deduped:
            return []

        if len(deduped) > settings.max_passages_for_embedding:
            deduped = deduped[: settings.max_passages_for_embedding]

        texts = [query] + [p.text for p in deduped]
        vectors = await asyncio.to_thread(
            _embed_texts,
            texts,
            settings.embed_batch_size,
        )
        query_vec = vectors[0]
        passage_vecs = vectors[1:]

        scored: list[Passage] = []
        for passage, vec in zip(deduped, passage_vecs, strict=True):
            score = _cosine_similarity(query_vec, vec)
            scored.append(passage.model_copy(update={"score": score}))

        scored.sort(key=lambda p: p.score or 0.0, reverse=True)
        relevant = [p for p in scored if (p.score or 0.0) >= settings.min_passage_score]
        return relevant[:k]


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
