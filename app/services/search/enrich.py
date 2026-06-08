import asyncio
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
import structlog

from app.models.schemas import Passage

logger = structlog.get_logger()

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}
MAX_BYTES = 500_000
MAX_TEXT_CHARS = 4000
FETCH_TIMEOUT = 10.0


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def get_text(self) -> str:
        raw = " ".join(self._chunks)
        return re.sub(r"\s+", " ", raw).strip()


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in BLOCKED_HOSTS:
        return False
    if host.endswith(".local"):
        return False
    return True


def _extract_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)
    return parser.get_text()


def _fetch_page_text(url: str) -> str:
    if not _is_safe_url(url):
        return ""

    headers = {"User-Agent": "MeridianResearch/0.1 (research-bot)"}
    with httpx.Client(timeout=FETCH_TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        content = response.content[:MAX_BYTES]
        html = content.decode(response.encoding or "utf-8", errors="ignore")
        text = _extract_text(html)
        return text[:MAX_TEXT_CHARS]


async def enrich_passages(passages: list[Passage], limit: int = 8) -> list[Passage]:
    enriched: list[Passage] = []

    async def enrich_one(passage: Passage) -> Passage:
        if not passage.url or passage.source != "duckduckgo":
            return passage
        try:
            extra = await asyncio.to_thread(_fetch_page_text, passage.url)
            if not extra or len(extra) < 100:
                return passage
            combined = f"{passage.text}\n\n{extra}"[:MAX_TEXT_CHARS]
            return passage.model_copy(update={"text": combined})
        except Exception as exc:
            logger.warning("enrich_failed", url=passage.url, error=str(exc))
            return passage

    targets = passages[:limit]
    results = await asyncio.gather(*[enrich_one(p) for p in targets])
    enriched.extend(results)
    enriched.extend(passages[limit:])
    return enriched
