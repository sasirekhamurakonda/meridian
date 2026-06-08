from enum import StrEnum
import re


class QueryIntent(StrEnum):
    RECOMMENDATION = "recommendation"
    FACTUAL = "factual"
    ACADEMIC = "academic"


RECOMMENDATION_HINTS = (
    "best", "top", "recommend", "which", "should i", "good", "popular",
    "compare", "vs", "versus", "pick", "choose", "favorite",
)

ACADEMIC_HINTS = (
    "research", "paper", "study", "theorem", "hypothesis", "quantum",
    "clinical", "meta-analysis",
)


def detect_intent(query: str) -> QueryIntent:
    q = query.lower()
    if any(hint in q for hint in RECOMMENDATION_HINTS):
        return QueryIntent.RECOMMENDATION
    if any(hint in q for hint in ACADEMIC_HINTS):
        return QueryIntent.ACADEMIC
    return QueryIntent.FACTUAL


def is_recommendation_query(query: str) -> bool:
    return detect_intent(query) == QueryIntent.RECOMMENDATION
