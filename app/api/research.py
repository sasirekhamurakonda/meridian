import asyncio
import json
import uuid
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse

from app.api.deps import verify_api_key
from app.config import get_settings
from app.db.redis_client import get_redis
from app.db.session import async_session_factory
from app.models.db import ResearchJob
from app.models.schemas import (
    JobStatus,
    ResearchCreatedResponse,
    ResearchJobResponse,
    ResearchReport,
    ResearchRequest,
)
from app.services.events import get_event_service
router = APIRouter(prefix="/research", tags=["research"])
limiter = Limiter(key_func=get_remote_address)
_rate_limit = f"{get_settings().rate_limit_per_hour}/hour"


def _job_to_response(job: ResearchJob) -> ResearchJobResponse:
    report = None
    if job.report_json:
        report = ResearchReport.model_validate(job.report_json)

    return ResearchJobResponse(
        id=job.id,
        query=job.query,
        status=JobStatus(job.status),
        progress=job.progress_json,
        report=report,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=ResearchCreatedResponse)
@limiter.limit(_rate_limit)
async def create_research(
    request: Request,
    body: ResearchRequest,
    _: None = Depends(verify_api_key),
) -> ResearchCreatedResponse:
    settings = get_settings()
    if len(body.query) > settings.max_query_length:
        raise HTTPException(status_code=400, detail="Query exceeds maximum length")

    job_id = uuid.uuid4()
    async with async_session_factory() as session:
        job = ResearchJob(id=job_id, query=body.query, status=JobStatus.QUEUED.value)
        session.add(job)
        await session.commit()

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    pool = await create_pool(redis_settings)
    try:
        await pool.enqueue_job(
            "run_research_job",
            str(job_id),
            body.query,
            body.max_sub_questions,
        )
    finally:
        await pool.aclose()

    return ResearchCreatedResponse(id=job_id, status=JobStatus.QUEUED)


@router.get("/{job_id}", response_model=ResearchJobResponse)
async def get_research(
    job_id: UUID,
    _: None = Depends(verify_api_key),
) -> ResearchJobResponse:
    async with async_session_factory() as session:
        job = await session.get(ResearchJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Research job not found")
        return _job_to_response(job)


@router.get("/{job_id}/stream")
async def stream_research(
    job_id: UUID,
    _: None = Depends(verify_api_key),
) -> EventSourceResponse:
    async with async_session_factory() as session:
        job = await session.get(ResearchJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Research job not found")

    events = get_event_service()
    redis = get_redis()
    channel = events.subscribe_channel(job_id)

    async def event_generator():
        history = await events.get_log(job_id)
        for event in history:
            yield {"event": event.status, "data": event.model_dump_json()}

        if job.status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
            yield {"event": "done", "data": json.dumps({"status": job.status})}
            return

        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=15.0,
                    )
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": "{}"}
                    continue

                if message and message.get("type") == "message":
                    payload = message["data"]
                    if isinstance(payload, bytes):
                        payload = payload.decode()
                    data = json.loads(payload)
                    yield {"event": data.get("status", "update"), "data": json.dumps(data)}

                    if data.get("stage") == "pipeline" and data.get("status") in ("done", "error"):
                        yield {"event": "done", "data": json.dumps(data)}
                        break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return EventSourceResponse(event_generator())
