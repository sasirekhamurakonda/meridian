from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.agents.critic import CriticAgent
from app.agents.planner import PlannerAgent
from app.models.schemas import ContradictionItem, CriticOutput, Passage, PlannerOutput
from app.pipeline.orchestrator import ResearchOrchestrator


@pytest.mark.asyncio
async def test_planner_parses_sub_questions():
    llm = AsyncMock()
    llm.complete_json = AsyncMock(
        return_value=PlannerOutput(
            sub_questions=[
                "What is quantum error correction?",
                "What are surface codes?",
                "What are recent advances?",
            ]
        )
    )
    planner = PlannerAgent(llm=llm)
    result = await planner.decompose("quantum error correction advances")
    assert len(result) == 3


@pytest.mark.asyncio
async def test_critic_returns_structured_output():
    llm = AsyncMock()
    llm.complete_json = AsyncMock(
        return_value=CriticOutput(
            contradictions=[
                ContradictionItem(
                    topic="timeline",
                    positions=["2024 breakthrough", "still theoretical"],
                )
            ],
            gaps=["Limited industrial deployment data"],
        )
    )
    critic = CriticAgent(llm=llm)
    result = await critic.analyze(
        "quantum error correction",
        [
            Passage(
                text="A breakthrough was announced in 2024.",
                url="https://example.com",
                title="Example",
                source="arxiv",
            )
        ],
    )
    assert len(result.contradictions) == 1
    assert result.gaps


@pytest.mark.asyncio
async def test_orchestrator_completes_pipeline():
    job_id = uuid4()
    orchestrator = ResearchOrchestrator()

    with (
        patch.object(orchestrator, "_update_status", new_callable=AsyncMock),
        patch.object(orchestrator, "_update_progress", new_callable=AsyncMock),
        patch.object(orchestrator, "_complete_job", new_callable=AsyncMock) as mock_complete,
        patch.object(orchestrator.planner, "decompose", new_callable=AsyncMock) as mock_plan,
        patch.object(orchestrator.researcher, "gather_all", new_callable=AsyncMock) as mock_gather,
        patch.object(orchestrator.extractor, "rank", new_callable=AsyncMock) as mock_rank,
        patch.object(orchestrator.critic, "analyze", new_callable=AsyncMock) as mock_critic,
        patch.object(orchestrator.synthesizer, "build", new_callable=AsyncMock) as mock_synth,
        patch.object(orchestrator.events, "publish", new_callable=AsyncMock),
    ):
        from datetime import UTC, datetime

        from app.models.schemas import ResearchReport

        mock_plan.return_value = ["q1", "q2", "q3"]
        mock_gather.return_value = [
            Passage(text="evidence", url="https://x.com", title="T", source="arxiv")
        ]
        mock_rank.return_value = mock_gather.return_value
        mock_critic.return_value = CriticOutput()
        mock_synth.return_value = ResearchReport(
            query="test",
            summary="summary",
            key_findings=["finding"],
            recommendations=[],
            evidence=[],
            contradictions=[],
            gaps=[],
            confidence="medium",
            generated_at=datetime.now(UTC),
        )

        await orchestrator.run(job_id, "test query")

    mock_complete.assert_awaited_once()
