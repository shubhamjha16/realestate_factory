"""
RE Graph — Real Estate Factory (Module Facade & Backward Compatibility Seam).

Re-exports `app` from `builder.py`.
"""

from __future__ import annotations

from app.services.graph import llm
from app.services.graph.builder import app, build_graph
from app.services.graph.state import REState


def _default_chat(messages: list, max_tokens: int = 4096, json_mode: bool = False) -> str:
    return llm.chat(messages, max_tokens=max_tokens, json_mode=json_mode)


_default_chat._is_default_facade = True  # type: ignore[attr-defined]

# Seam for cassette runner and direct calls
_chat = _default_chat

__all__ = ["app", "build_graph", "REState", "_chat"]
