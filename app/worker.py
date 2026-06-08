from uuid import UUID

import structlog
from arq.connections import RedisSettings

from app.config import get_settings
from app.pipeline.orchestrator import ResearchOrchestrator

logger = structlog.get_logger()


async def run_research_job(
    ctx: dict,
    job_id: str,
    query: str,
    max_sub_questions: int | None = None,
) -> None:
    logger.info("worker_job_started", job_id=job_id)
    orchestrator = ResearchOrchestrator()
    await orchestrator.run(UUID(job_id), query, max_sub_questions)


async def startup(ctx: dict) -> None:
    logger.info("worker_startup")


async def shutdown(ctx: dict) -> None:
    logger.info("worker_shutdown")


class WorkerSettings:
    functions = [run_research_job]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = get_settings().max_concurrent_jobs
    job_timeout = get_settings().job_timeout_seconds
    cron_jobs = []
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)


def get_worker_settings() -> type[WorkerSettings]:
    return WorkerSettings
