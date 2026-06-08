import json
from datetime import UTC, datetime
from uuid import UUID

from app.config import get_settings
from app.db.redis_client import get_redis
from app.models.schemas import PipelineEvent


class EventService:
    def _log_key(self, job_id: UUID) -> str:
        return f"research:{job_id}:log"

    def _channel(self, job_id: UUID) -> str:
        return f"research:{job_id}:events"

    async def publish(
        self,
        job_id: UUID,
        stage: str,
        status: str,
        data: dict | None = None,
    ) -> PipelineEvent:
        event = PipelineEvent(
            stage=stage,
            status=status,
            data=data or {},
            timestamp=datetime.now(UTC),
        )
        redis = get_redis()
        payload = event.model_dump_json()
        settings = get_settings()

        async with redis.pipeline(transaction=True) as pipe:
            pipe.rpush(self._log_key(job_id), payload)
            pipe.expire(self._log_key(job_id), settings.event_log_ttl_seconds)
            pipe.publish(self._channel(job_id), payload)
            await pipe.execute()

        return event

    async def get_log(self, job_id: UUID) -> list[PipelineEvent]:
        redis = get_redis()
        entries = await redis.lrange(self._log_key(job_id), 0, -1)
        return [PipelineEvent.model_validate(json.loads(entry)) for entry in entries]

    def subscribe_channel(self, job_id: UUID) -> str:
        return self._channel(job_id)


_event_service: EventService | None = None


def get_event_service() -> EventService:
    global _event_service
    if _event_service is None:
        _event_service = EventService()
    return _event_service
