"""
Typed environment configuration.

Every environment read in the application happens here, once, through
pydantic-settings. A missing required variable is a boot failure that names the
variable — not a silent empty string that surfaces four nodes later as a 401
from a provider.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ── Required ──────────────────────────────────────────────────────────────
    # The router LLM runs intake on every job, on every path. Without it nothing
    # generates, so it is a boot requirement rather than a runtime surprise.
    GROQ_API_KEY: str = Field(min_length=1)

    # ── LLM ───────────────────────────────────────────────────────────────────
    ROUTER_MODEL: str = "llama-3.3-70b-versatile"
    DRAFTER_MODEL: str = "claude-sonnet-4-5"
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    # Golden runs are only a proof of anything if they are reproducible; the
    # sprint plan fixes them at 0.2. See backend/tests/golden/README.md.
    LLM_TEMPERATURE: float = 0.2
    MAX_CRITIC_RETRIES: int = 2
    MAX_HEALER_RETRIES: int = 2

    # ── Storage ───────────────────────────────────────────────────────────────
    S3_BUCKET: str = ""
    AWS_REGION: str = "ap-south-1"
    KMS_KEY_ID: str = ""
    PRESIGN_TTL_SECONDS: int = 900
    OUTPUT_DIR: str = "output"

    # ── Infrastructure (wired in S2 and S4) ───────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://realestate:realestate@localhost:5433/realestate"
    REDIS_URL: str = "redis://localhost:6380/0"

    # ── Valuation policy (enforced from S6/S7) ────────────────────────────────
    ROUNDING_POLICY: Literal["half_up", "half_even"] = "half_up"
    MONEY_DP: int = 2
    DEFAULT_AREA_UNIT: str = "sqft"
    COMPARABLE_RADIUS_M: int = 2000
    COMPARABLE_MIN_SAMPLE: int = 3
    COMPARABLE_MAX_AGE_MONTHS: int = 18

    # ── HTTP ──────────────────────────────────────────────────────────────────
    PORT: int = 8004
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    WEBHOOK_URL: str = ""
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("LLM_TEMPERATURE")
    @classmethod
    def _sane_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("must be between 0.0 and 2.0")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached accessor. Import-time failure is deliberate: the process must not
    reach the point of accepting a request with a half-configured engine.
    """
    try:
        return Settings()  # type: ignore[call-arg]  # populated from the environment
    except Exception as exc:  # pydantic ValidationError, or a bad .env
        missing = _missing_names(exc)
        detail = ", ".join(missing) if missing else str(exc)
        print(
            f"FATAL: configuration error — {detail}\n"
            f"       Set it in backend/.env (see backend/.env.example) or the process "
            f"environment, then start again.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


def _missing_names(exc: Exception) -> list[str]:
    errors = getattr(exc, "errors", None)
    if not callable(errors):
        return []
    names = []
    for err in errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        names.append(f"{loc} is {err.get('msg', 'invalid')}")
    return names


settings = get_settings()
