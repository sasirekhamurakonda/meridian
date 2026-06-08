from app.services.embeddings import EmbeddingService, get_embedding_service
from app.models.schemas import Passage


class ExtractorAgent:
    def __init__(self, embeddings: EmbeddingService | None = None) -> None:
        self.embeddings = embeddings or get_embedding_service()

    async def rank(self, query: str, passages: list[Passage], top_k: int | None = None) -> list[Passage]:
        return await self.embeddings.rank(query, passages, top_k=top_k)
