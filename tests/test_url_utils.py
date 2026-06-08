import pytest

from app.url_utils import validate_database_url, validate_redis_url


def test_validate_database_url_accepts_neon_host() -> None:
    url = (
        "postgresql+asyncpg://user:secret@ep-example-pooler.ap-southeast-1.aws.neon.tech/"
        "neondb?ssl=require"
    )
    assert validate_database_url(url) == url


def test_validate_database_url_rejects_unencoded_password_at_sign() -> None:
    with pytest.raises(ValueError, match="hostname is empty|malformed"):
        validate_database_url(
            "postgresql+asyncpg://user:pass@word@ep-example.neon.tech/neondb?ssl=require"
        )


def test_validate_redis_url_requires_tls_for_upstash() -> None:
    with pytest.raises(ValueError, match="rediss://"):
        validate_redis_url("redis://default:token@example.upstash.io:6379")


def test_validate_redis_url_accepts_upstash_tls() -> None:
    url = "rediss://default:token@example.upstash.io:6379"
    assert validate_redis_url(url) == url
