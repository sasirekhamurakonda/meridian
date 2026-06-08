from fastapi import APIRouter
from sqlalchemy import text

from app.db.redis_client import get_redis
from app.db.session import engine
from app.services.llm import get_llm

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, object]:
    checks: dict[str, object] = {"postgres": False, "redis": False, "llm": False}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception:
        pass

    try:
        redis = get_redis()
        checks["redis"] = bool(await redis.ping())
    except Exception:
        pass

    try:
        checks["llm"] = await get_llm().health_check()
    except Exception:
        pass

    all_ready = all(checks.values())
    return {"status": "ready" if all_ready else "degraded", "checks": checks}
