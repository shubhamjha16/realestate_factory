#!/usr/bin/env python
"""
Write the OpenAPI spec to a file.

`packages/api-types` is generated from this, and CI regenerates and diffs. That
is the gate §3 describes: a backend schema change the console has not caught up
with fails the build, rather than becoming a runtime surprise in front of a
valuer.

Importing the app requires GROQ_API_KEY to be set, by design — but nothing here
calls a provider, so any non-empty value works in CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = BACKEND_ROOT.parent / "packages" / "api-types" / "openapi.json"


def main() -> int:
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.main import create_app

    spec = create_app().openapi()

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys so the file is stable and the CI diff means something.
    out.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out.relative_to(BACKEND_ROOT.parent)} ({len(spec['paths'])} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
