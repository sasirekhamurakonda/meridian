import asyncio

import structlog
import wikipediaapi

from app.config import get_settings
from app.models.schemas import Passage

logger = structlog.get_logger()


async def search_wikipedia(query: str, sub_question: str) -> list[Passage]:
    settings = get_settings()

    def _search() -> list[Passage]:
        wiki = wikipediaapi.Wikipedia(
            user_agent="MeridianResearch/0.1 (research-api)",
            language="en",
            extract_format=wikipediaapi.ExtractFormat.WIKI,
        )
        page = wiki.page(query)
        if not page.exists():
            results = wiki.search(query, results=settings.max_results_per_source)
            passages: list[Passage] = []
            for title in results[: settings.max_results_per_source]:
                candidate = wiki.page(title)
                if candidate.exists() and candidate.summary:
                    passages.append(
                        Passage(
                            text=candidate.summary[:3000],
                            url=candidate.fullurl,
                            title=candidate.title,
                            source="wikipedia",
                            sub_question=sub_question,
                        )
                    )
            return passages

        summary = page.summary or page.text[:3000]
        return [
            Passage(
                text=summary[:3000],
                url=page.fullurl,
                title=page.title,
                source="wikipedia",
                sub_question=sub_question,
            )
        ]

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_search),
            timeout=settings.search_timeout_seconds,
        )
    except Exception as exc:
        logger.warning("wikipedia_search_failed", query=query, error=str(exc))
        return []
