#!/usr/bin/env python3
"""Validate cloud env vars and print safe connection diagnostics."""

from __future__ import annotations

import sys

from sqlalchemy.engine.url import make_url

from app.config import get_settings


def main() -> int:
    try:
        settings = get_settings()
    except Exception as exc:
        print(f"ERROR: Invalid environment configuration: {exc}")
        return 1

    db = make_url(settings.database_url)
    redis_host = settings.redis_url.split("@")[-1].split("/")[0].split(":")[0]

    print(f"DATABASE_URL driver: {db.drivername}")
    print(f"DATABASE_URL host: {db.host}")
    print(f"DATABASE_URL database: {db.database}")
    print(f"REDIS_URL host: {redis_host}")
    print(f"LLM_API_KEY set: {'yes' if settings.llm_api_key else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
