import json
import re
from typing import TypeVar

import certifi
import httpx
import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import get_settings

logger = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)


class LLMService:
    def __init__(self) -> None:
        settings = get_settings()
        ssl_verify: str | bool = certifi.where() if settings.llm_ssl_verify else False
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-needed",
            timeout=120.0,
            max_retries=2,
            http_client=httpx.AsyncClient(verify=ssl_verify),
        )
        self._model = settings.llm_model

    async def complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM returned empty response")
        return content.strip()

    async def complete_json(
        self,
        system: str,
        user: str,
        schema: type[T],
        temperature: float = 0.2,
    ) -> T:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                raw = await self.complete(
                    system=system,
                    user=user if attempt == 0 else self._repair_prompt(user, last_error),
                    temperature=temperature,
                )
                parsed = self._parse_json(raw)
                return schema.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
                logger.warning("llm_json_parse_failed", attempt=attempt + 1, error=str(exc))
        raise ValueError(f"Failed to parse LLM JSON output: {last_error}")

    def _repair_prompt(self, original: str, error: Exception | None) -> str:
        return (
            f"{original}\n\n"
            "Your previous response was invalid. Return ONLY valid JSON matching the schema. "
            f"Error: {error}"
        )

    def _parse_json(self, raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False


_llm: LLMService | None = None


def get_llm() -> LLMService:
    global _llm
    if _llm is None:
        _llm = LLMService()
    return _llm
