from uuid import UUID

import structlog
from sqlalchemy import update

from app.agents.critic import CriticAgent
from app.agents.extractor import ExtractorAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.synthesizer import SynthesizerAgent
from app.config import get_settings
from app.db.session import async_session_factory
from app.models.db import ResearchJob
from app.models.schemas import JobStatus
from app.services.events import get_event_service
from app.services.query_intent import is_recommendation_query
from app.services.search.enrich import enrich_passages

logger = structlog.get_logger()


class ResearchOrchestrator:
    def __init__(self) -> None:
        self.events = get_event_service()
        self.planner = PlannerAgent()
        self.researcher = ResearcherAgent(self.events)
        self.extractor = ExtractorAgent()
        self.critic = CriticAgent()
        self.synthesizer = SynthesizerAgent()

    async def run(self, job_id: UUID, query: str, max_sub_questions: int | None = None) -> None:
        settings = get_settings()
        try:
            await self._update_status(job_id, JobStatus.PLANNING)
            await self.events.publish(job_id, "planner", "started", {"query": query})

            sub_questions = await self.planner.decompose(query, max_sub_questions)
            await self._update_progress(job_id, {"sub_questions": sub_questions})
            await self.events.publish(
                job_id, "planner", "completed", {"sub_questions": sub_questions}
            )

            await self._update_status(job_id, JobStatus.RESEARCHING)
            raw_passages = await self.researcher.gather_all(job_id, query, sub_questions)
            await self._update_progress(job_id, {"raw_passage_count": len(raw_passages)})

            await self._update_status(job_id, JobStatus.EXTRACTING)
            await self.events.publish(job_id, "extractor", "started", {})
            ranked = await self.extractor.rank(query, raw_passages, top_k=settings.top_k_passages)
            if is_recommendation_query(query) and ranked:
                ranked = await enrich_passages(ranked, limit=8)
            await self.events.publish(
                job_id, "extractor", "completed", {"top_passages": len(ranked)}
            )

            await self._update_status(job_id, JobStatus.CRITIQUING)
            await self.events.publish(job_id, "critic", "started", {})
            critique = await self.critic.analyze(query, ranked)
            await self.events.publish(
                job_id,
                "critic",
                "completed",
                {
                    "contradictions": [c.model_dump() for c in critique.contradictions],
                    "gaps": critique.gaps,
                },
            )

            await self._update_status(job_id, JobStatus.SYNTHESIZING)
            await self.events.publish(job_id, "synthesizer", "started", {})
            report = await self.synthesizer.build(query, ranked, critique)
            await self.events.publish(
                job_id,
                "synthesizer",
                "completed",
                {"report": report.model_dump(mode="json")},
            )

            await self._complete_job(job_id, report.model_dump(mode="json"))
            await self.events.publish(job_id, "pipeline", "done", {})
            logger.info("research_completed", job_id=str(job_id))

        except Exception as exc:
            logger.exception("research_failed", job_id=str(job_id), error=str(exc))
            await self._fail_job(job_id, "Research job failed. Check logs for details.")
            await self.events.publish(job_id, "pipeline", "error", {"message": "Job failed"})
            raise

    async def _update_status(self, job_id: UUID, status: JobStatus) -> None:
        async with async_session_factory() as session:
            await session.execute(
                update(ResearchJob).where(ResearchJob.id == job_id).values(status=status.value)
            )
            await session.commit()

    async def _update_progress(self, job_id: UUID, progress: dict) -> None:
        async with async_session_factory() as session:
            job = await session.get(ResearchJob, job_id)
            if job:
                existing = job.progress_json or {}
                existing.update(progress)
                job.progress_json = existing
                await session.commit()

    async def _complete_job(self, job_id: UUID, report: dict) -> None:
        async with async_session_factory() as session:
            await session.execute(
                update(ResearchJob)
                .where(ResearchJob.id == job_id)
                .values(status=JobStatus.COMPLETED.value, report_json=report, error=None)
            )
            await session.commit()

    async def _fail_job(self, job_id: UUID, error: str) -> None:
        async with async_session_factory() as session:
            await session.execute(
                update(ResearchJob)
                .where(ResearchJob.id == job_id)
                .values(status=JobStatus.FAILED.value, error=error)
            )
            await session.commit()
