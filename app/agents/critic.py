from app.agents.base import BaseAgent
from app.models.schemas import CriticOutput, Passage
from app.services.query_intent import is_recommendation_query


class CriticAgent(BaseAgent):
    SYSTEM_PROMPT = (
        "You are a research critic. Identify genuine factual contradictions between "
        "sources and knowledge gaps. A contradiction means two sources disagree on the "
        "same fact (e.g. different dates, conflicting rankings claimed as definitive). "
        "Different list sizes (top 8 vs top 10) or overlapping recommendations are NOT "
        "contradictions. Return empty contradictions if sources merely differ in scope. "
        "Return JSON only."
    )

    async def analyze(self, query: str, passages: list[Passage]) -> CriticOutput:
        evidence_text = "\n\n".join(
            f"[{p.source}] {p.title} ({p.url}): {p.text[:1200]}" for p in passages[:12]
        )
        extra = ""
        if is_recommendation_query(query):
            extra = (
                "\nThis is a recommendation query. Focus gaps on missing comparisons, "
                "unclear winners, or channels mentioned without explanation."
            )

        user_prompt = (
            f'Research query: "{query}"\n\n'
            f"Evidence:\n{evidence_text}\n"
            f"{extra}\n\n"
            'Return JSON: {"contradictions": [{"topic": "...", "positions": ["...", "..."]}], '
            '"gaps": ["..."]}'
        )
        return await self.llm.complete_json(
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
            schema=CriticOutput,
        )
