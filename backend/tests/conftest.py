from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# `intake_node` builds its prompt with `', '.join(ALL_JOB_TYPES)` over a set, so
# the prompt text — and therefore the whole run — differs between processes under
# Python's string hash randomisation, and the golden cassettes stop matching.
#
# The seed has to be set before the interpreter starts, so it cannot be fixed
# from here; re-exec'ing would work but pytest has already replaced stdout by the
# time conftest is imported, and the re-exec'd run reports nothing at all. Fail
# loudly instead. `make test` and CI both set it.
#
# The underlying instability is a real defect — it also defeats prompt caching —
# and belongs to S10, where prompts become data.
if os.environ.get("PYTHONHASHSEED") != "0":
    raise RuntimeError(
        "PYTHONHASHSEED must be 0 for the golden set to be reproducible.\n"
        "  run: PYTHONHASHSEED=0 pytest      (or: make test)"
    )

# The engine must import without a provider key present; golden runs replace the
# LLM entirely, so the value is never used to make a call.
os.environ.setdefault("GROQ_API_KEY", "test-no-live-calls")
# Required from S5. A real deployment has no default; the tests need *a* value,
# and one that is obviously not a secret.
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-any-real-use")

sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "tests" / "golden"))
