"""
Typed config: fail at boot, naming the variable.

Run in a subprocess because the failure is a process exit — which is the point.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _boot(env_overrides: dict) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "GROQ_API_KEY"}
    env.update(env_overrides)
    # An .env in the working tree would satisfy the setting and mask the failure.
    env["PYTHONPATH"] = str(BACKEND_ROOT)
    return subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=BACKEND_ROOT / "tests",
        env=env,
        capture_output=True,
        text=True,
    )


def test_boot_without_groq_api_key_exits_non_zero_naming_the_variable():
    result = _boot({})
    assert result.returncode != 0
    assert "GROQ_API_KEY" in result.stderr


def test_boot_with_groq_api_key_succeeds():
    assert _boot({"GROQ_API_KEY": "present"}).returncode == 0


def test_settings_are_typed_not_strings():
    from app.configs.envConfig import settings

    assert isinstance(settings.PORT, int)
    assert isinstance(settings.LLM_TEMPERATURE, float)
    assert isinstance(settings.COMPARABLE_MIN_SAMPLE, int)
    assert settings.cors_origin_list == [
        o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()
    ]


def test_job_type_registry_matches_the_four_paths():
    from app.configs.jobTypes import (
        AGREEMENT_TYPES,
        ALL_JOB_TYPES,
        ALL_JOB_TYPES_SORTED,
        COMPLIANCE_TYPES,
        RECONCILIATION_TYPES,
        VALUATION_TYPES,
    )

    assert len(VALUATION_TYPES) == 3
    assert len(COMPLIANCE_TYPES) == 5
    assert len(AGREEMENT_TYPES) == 6
    assert len(RECONCILIATION_TYPES) == 2
    assert len(ALL_JOB_TYPES) == 16
    # The sorted view exists because set order is not stable across processes.
    assert ALL_JOB_TYPES_SORTED == tuple(sorted(ALL_JOB_TYPES))
