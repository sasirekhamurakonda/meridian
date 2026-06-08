from app.services.llm import LLMService, get_llm


class BaseAgent:
    def __init__(self, llm: LLMService | None = None) -> None:
        self.llm = llm or get_llm()
