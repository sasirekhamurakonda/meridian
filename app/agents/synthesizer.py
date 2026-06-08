from datetime import UTC, datetime

from app.agents.base import BaseAgent
from app.models.schemas import (
    CriticOutput,
    Passage,
    RecommendationItem,
    ResearchReport,
    SynthesizerOutput,
)
from app.services.query_intent import is_recommendation_query


class SynthesizerAgent(BaseAgent):
    SYSTEM_PROMPT = (
        "You are a research synthesizer. Build a structured, evidence-backed report. "
        "Only make claims directly supported by the provided sources. "
        "Never invent names, numbers, or facts not present in the evidence. "
        "Return JSON only."
    )

    RECOMMENDATION_PROMPT = (
        "This is a recommendation/ranking query. You MUST:\n"
        "1. Give a direct answer in summary naming the top pick and 2-3 runners-up.\n"
        "2. Format key_findings as a ranked list: '1. Name — why it's recommended'.\n"
        "3. Populate recommendations with structured entries (name, rank, reason, best_for).\n"
        "4. Use medium confidence if multiple sources agree on top channels; high if consensus is strong.\n"
        "5. Only include channels explicitly named in the evidence."
    )

    async def build(
        self,
        query: str,
        passages: list[Passage],
        critique: CriticOutput,
    ) -> ResearchReport:
        if not passages:
            evidence_text = "(No relevant evidence found.)"
        else:
            evidence_text = "\n\n".join(
                f"[{p.source}] score={p.score:.2f} {p.title} ({p.url}):\n{p.text[:2000]}"
                for p in passages
                if p.score is not None
            )

        contradictions = [c.model_dump() for c in critique.contradictions]
        intent_note = ""
        if is_recommendation_query(query):
            intent_note = f"\n\n{self.RECOMMENDATION_PROMPT}"

        user_prompt = (
            f'Query: "{query}"\n\n'
            f"Ranked evidence:\n{evidence_text}\n\n"
            f"Contradictions: {contradictions}\n"
            f"Gaps: {critique.gaps}\n"
            f"{intent_note}\n\n"
            "Return JSON with fields: summary, key_findings, recommendations "
            "(list of {name, rank, reason, best_for, sources: [{url, title, excerpt}]}), "
            "evidence (list of {claim, sources: [{url, title, excerpt}]}), "
            "contradictions, gaps, confidence (high|medium|low)."
        )

        raw = await self.llm.complete_json(
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
            schema=SynthesizerOutput,
        )
        return ResearchReport(
            query=query,
            summary=raw.summary,
            key_findings=raw.key_findings,
            recommendations=raw.recommendations,
            evidence=raw.evidence,
            contradictions=raw.contradictions,
            gaps=raw.gaps,
            confidence=raw.confidence,
            generated_at=datetime.now(UTC),
        )
