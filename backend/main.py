"""Entrypoint. `python main.py`, or `uvicorn app.main:app` in deployment."""

from __future__ import annotations

import uvicorn

from app.configs.envConfig import settings

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT)
