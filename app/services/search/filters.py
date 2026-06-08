import re

from app.models.schemas import Passage

JUNK_URL_PATTERNS = [
    re.compile(r"bestbuy\.com", re.I),
    re.compile(r"amazon\.com/(?:gp/|s\?|b\?)", re.I),
    re.compile(r"google\.com/translate", re.I),
    re.compile(r"bing\.com/aclick", re.I),
    re.compile(r"youtube\.com/(?:about|t/|howyoutubeworks|creators|ads)", re.I),
    re.compile(r"^https?://(?:www\.)?youtube\.com/?$", re.I),
]

STOPWORDS = {
    "the", "a", "an", "for", "and", "or", "to", "of", "in", "on", "is", "are",
    "best", "what", "how", "which", "where", "when", "why", "with", "from",
}


def _query_keywords(query: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", query.lower())
    return {w for w in words if w not in STOPWORDS}


def is_junk_url(url: str) -> bool:
    if not url:
        return True
    return any(pattern.search(url) for pattern in JUNK_URL_PATTERNS)


def passage_matches_query(passage: Passage, query: str) -> bool:
    keywords = _query_keywords(query)
    if not keywords:
        return True

    haystack = f"{passage.title} {passage.text} {passage.url}".lower()
    matches = sum(1 for kw in keywords if kw in haystack)
    required = max(1, min(2, len(keywords) // 3))
    return matches >= required


def filter_passages(passages: list[Passage], query: str) -> list[Passage]:
    filtered: list[Passage] = []
    for passage in passages:
        if is_junk_url(passage.url):
            continue
        if not passage_matches_query(passage, query):
            continue
        filtered.append(passage)
    return filtered
