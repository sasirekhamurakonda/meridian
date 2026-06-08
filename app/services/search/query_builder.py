import re

PRACTICAL_HINTS = (
    "youtube", "channel", "tutorial", "course", "best", "top", "recommend",
    "how to", "guide", "review", "reddit", "blog", "podcast", "interview prep",
)

ACADEMIC_HINTS = (
    "research", "paper", "study", "theorem", "hypothesis", "quantum",
    "molecule", "clinical trial", "meta-analysis", "arxiv",
)


def is_academic_query(query: str) -> bool:
    q = query.lower()
    if any(hint in q for hint in PRACTICAL_HINTS):
        return False
    return any(hint in q for hint in ACADEMIC_HINTS)


def mentions_youtube(query: str) -> bool:
    return "youtube" in query.lower() or "youtu.be" in query.lower()


def build_web_queries(original_query: str, sub_question: str) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        normalized = " ".join(q.split()).strip()
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            queries.append(normalized)

    add(sub_question)
    add(original_query)

    if mentions_youtube(original_query) or mentions_youtube(sub_question):
        topic = _extract_topic(original_query, sub_question)
        add(f"site:youtube.com {topic}")
        add(f"best youtube channels {topic}")
        add(f"{topic} youtube channel recommendations")

    if "system design" in original_query.lower() or "system design" in sub_question.lower():
        add("best youtube channels system design interview")
        add("system design interview preparation youtube channels")
        add("reddit best youtube channel system design interview")
        add("top system design youtube channels Gaurav Sen ByteByteGo Neo Kim")

    if is_recommendation_style(original_query):
        add(f"reddit {original_query}")
        add(f"best { _extract_topic(original_query, sub_question) } ranked list")

    return queries[:6]


def is_recommendation_style(query: str) -> bool:
    q = query.lower()
    return any(w in q for w in ("best", "top", "recommend", "which", "good"))


def _extract_topic(original_query: str, sub_question: str) -> str:
    text = sub_question if len(sub_question) > len(original_query) else original_query
    text = re.sub(r"\byoutube\b", "", text, flags=re.I)
    text = re.sub(r"\bchannel(s)?\b", "", text, flags=re.I)
    text = re.sub(r"\bbest\b", "", text, flags=re.I)
    return " ".join(text.split()).strip() or original_query
