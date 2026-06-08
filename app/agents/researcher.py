import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID

import structlog

from app.models.schemas import Passage
from app.services.events import EventService
from app.services.search import search_arxiv, search_duckduckgo, search_wikipedia
from app.services.search.query_builder import is_academic_query

logger = structlog.get_logger()


class ResearcherAgent:
    def __init__(self, events: EventService) -> None:
        self.events = events

    async def gather_all(
        self,
        job_id: UUID,
        original_query: str,
        sub_questions: list[str],
    ) -> list[Passage]:
        all_passages: list[Passage] = []

        primary = await self._gather_one(job_id, original_query, original_query)
        all_passages.extend(primary)

        tasks = [
            self._gather_one(job_id, original_query, sub_question)
            for sub_question in sub_questions
            if sub_question.strip().lower() != original_query.strip().lower()
        ]
        if tasks:
            results = await asyncio.gather(*tasks)
            for passages in results:
                all_passages.extend(passages)

        await self.events.publish(
            job_id,
            stage="researcher",
            status="completed",
            data={"total_passages": len(all_passages)},
        )
        return all_passages

    async def _gather_one(
        self,
        job_id: UUID,
        original_query: str,
        sub_question: str,
    ) -> list[Passage]:
        use_academic = is_academic_query(original_query)
        sources: list[tuple[str, Callable[..., Awaitable[list[Passage]]]]] = [
            ("duckduckgo", search_duckduckgo),
        ]
        if use_academic:
            sources.extend([
                ("wikipedia", search_wikipedia),
                ("arxiv", search_arxiv),
            ])

        tasks = [
            search_fn(original_query, sub_question) if search_fn is search_duckduckgo
            else search_fn(sub_question, sub_question)
            for _, search_fn in sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        passages: list[Passage] = []
        for (source_name, _), result in zip(sources, results, strict=True):
            if isinstance(result, Exception):
                logger.warning("source_search_error", source=source_name, error=str(result))
                count = 0
            else:
                count = len(result)
                passages.extend(result)

            await self.events.publish(
                job_id,
                stage="researcher",
                status="progress",
                data={"source": source_name, "sub_question": sub_question, "count": count},
            )

        return passages
