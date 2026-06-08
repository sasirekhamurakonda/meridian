import asyncio

import structlog
from ddgs import DDGS

from app.config import get_settings
from app.models.schemas import Passage
from app.services.search.filters import filter_passages
from app.services.search.query_builder import build_web_queries

logger = structlog.get_logger()


async def search_duckduckgo(
    original_query: str,
    sub_question: str,
) -> list[Passage]:
    settings = get_settings()
    search_queries = build_web_queries(original_query, sub_question)

    def _search() -> list[Passage]:
        passages: list[Passage] = []
        seen_urls: set[str] = set()

        with DDGS() as ddgs:
            for search_query in search_queries:
                try:
                    results = ddgs.text(search_query, max_results=settings.max_web_results_per_query)
                except Exception as exc:
                    logger.warning("ddgs_query_failed", query=search_query, error=str(exc))
                    continue

                for item in results:
                    url = (item.get("href") or "").strip()
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    body = (item.get("body") or "").strip()
                    title = (item.get("title") or "Untitled").strip()
                    if not body and not title:
                        continue

                    text = body or title
                    passages.append(
                        Passage(
                            text=text[:3000],
                            url=url,
                            title=title,
                            source="duckduckgo",
                            sub_question=sub_question,
                        )
                    )

        return filter_passages(passages, original_query)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_search),
            timeout=settings.search_timeout_seconds,
        )
    except Exception as exc:
        logger.warning("duckduckgo_search_failed", query=sub_question, error=str(exc))
        return []
