import asyncio

import arxiv
import structlog

from app.config import get_settings
from app.models.schemas import Passage

logger = structlog.get_logger()


async def search_arxiv(query: str, sub_question: str) -> list[Passage]:
    settings = get_settings()

    def _search() -> list[Passage]:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=settings.max_results_per_source,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        passages: list[Passage] = []
        for result in client.results(search):
            summary = result.summary.strip()
            passages.append(
                Passage(
                    text=summary[:3000],
                    url=result.entry_id,
                    title=result.title,
                    source="arxiv",
                    sub_question=sub_question,
                )
            )
        return passages

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_search),
            timeout=settings.search_timeout_seconds,
        )
    except Exception as exc:
        logger.warning("arxiv_search_failed", query=query, error=str(exc))
        return []
