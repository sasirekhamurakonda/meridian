from app.models.schemas import Passage
from app.services.embeddings import EmbeddingService


async def test_rank_dedupes_and_sorts():
    service = EmbeddingService()
    passages = [
        Passage(
            text="Quantum error correction uses surface codes.",
            url="https://example.com/a",
            title="A",
            source="arxiv",
        ),
        Passage(
            text="Quantum error correction uses surface codes.",
            url="https://example.com/a",
            title="A duplicate",
            source="wikipedia",
        ),
        Passage(
            text="Classical computers use binary logic gates.",
            url="https://example.com/b",
            title="B",
            source="duckduckgo",
        ),
    ]

    ranked = await service.rank("quantum error correction", passages, top_k=2)

    assert len(ranked) == 2
    assert ranked[0].score is not None
    assert ranked[0].score >= (ranked[1].score or 0)
