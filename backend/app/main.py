"""
Application factory.

Importing this module imports `envConfig`, which is where a missing required
variable stops the process. That is intentional: the engine must fail at boot,
naming the variable, rather than accept a request it cannot serve.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.configs.envConfig import settings
from app.routers import api_router, legacy_router


def create_app() -> FastAPI:
    application = FastAPI(title="Real Estate Factory", version="1.0.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    application.include_router(api_router)
    application.include_router(legacy_router)
    return application


app = create_app()
