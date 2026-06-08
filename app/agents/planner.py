from app.agents.base import BaseAgent
from app.config import get_settings
from app.models.schemas import PlannerOutput


class PlannerAgent(BaseAgent):
    SYSTEM_PROMPT = (
        "You are a research planner. Decompose the user's question into focused "
        "sub-questions optimized for web search. For product/channel/tutorial questions, "
        "include specific searches (e.g. site names, comparisons, recommendations). "
        "For academic topics, include definitional and evidence-focused sub-questions. "
        "Return JSON only."
    )

    async def decompose(self, query: str, max_sub_questions: int | None = None) -> list[str]:
        settings = get_settings()
        target = max_sub_questions or settings.max_sub_questions
        target = max(settings.min_sub_questions, min(target, settings.max_sub_questions))

        user_prompt = (
            f'Query: "{query}"\n\n'
            f"Return JSON: {{\"sub_questions\": [\"...\"]}} with exactly {target} "
            "distinct, searchable sub-questions."
        )

        result = await self.llm.complete_json(
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
            schema=PlannerOutput,
        )
        return result.sub_questions
