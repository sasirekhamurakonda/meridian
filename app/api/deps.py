import secrets

from fastapi import Header, HTTPException, Query, status

from app.config import get_settings


async def verify_api_key(
    x_api_key: str | None = Header(default=None),
    api_key: str | None = Query(default=None),
) -> None:
    settings = get_settings()
    if not settings.api_key:
        return
    provided = x_api_key or api_key
    if not provided or not secrets.compare_digest(provided, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
