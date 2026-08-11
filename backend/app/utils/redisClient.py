"""Redis connection settings, shared by the web process and the worker."""

from __future__ import annotations

from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.configs.envConfig import settings


def redis_settings() -> RedisSettings:
    parsed = urlparse(settings.REDIS_URL)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0),
        ssl=parsed.scheme == "rediss",
    )
