from urllib.parse import urlparse

from sqlalchemy.engine.url import make_url


def _strip_wrapping(value: str) -> str:
    return value.strip().strip('"').strip("'")


def validate_database_url(url: str) -> str:
    cleaned = _strip_wrapping(url)
    if not cleaned:
        raise ValueError("DATABASE_URL is empty.")

    try:
        parsed = make_url(cleaned)
    except Exception as exc:
        raise ValueError(
            "DATABASE_URL is not a valid SQLAlchemy URL. "
            "Use postgresql+asyncpg://user:password@host/db?ssl=require"
        ) from exc

    host = parsed.host
    if not host:
        raise ValueError(
            "DATABASE_URL hostname is empty. This usually means your Neon password "
            "contains unencoded special characters (@, #, /, or %). "
            "URL-encode the password: @ → %40, # → %23, / → %2F, % → %25."
        )

    if "@" in host or " " in host or len(host) > 253:
        raise ValueError(
            f"DATABASE_URL hostname looks malformed ({host!r}). "
            "Re-copy the Neon connection string and URL-encode special characters in the password."
        )

    driver = parsed.drivername or ""
    if "asyncpg" not in driver:
        raise ValueError(
            f"DATABASE_URL must use the asyncpg driver (postgresql+asyncpg://), not {driver!r}."
        )

    return cleaned


def validate_redis_url(url: str) -> str:
    cleaned = _strip_wrapping(url)
    if not cleaned:
        raise ValueError("REDIS_URL is empty.")

    parsed = urlparse(cleaned)
    if parsed.scheme not in {"redis", "rediss"}:
        raise ValueError("REDIS_URL must start with redis:// or rediss://.")

    host = parsed.hostname
    if not host:
        raise ValueError(
            "REDIS_URL hostname is empty. URL-encode special characters in the Upstash token/password."
        )

    if "upstash.io" in host and parsed.scheme != "rediss":
        raise ValueError("Upstash requires a TLS URL: use rediss://, not redis://.")

    return cleaned
