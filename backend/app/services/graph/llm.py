"""
The graph's one call into a model.

Every node goes through `chat`, and nothing else in `graph/` constructs a client.
Two reasons beyond tidiness:

  · **It is the seam the golden set replaces.** Tests patch `llm.chat` or `reGraph._chat`,
    so every node is covered by one substitution rather than one per module.
  · **It is where the ledger sits.** S11 records a `cost_entries` row per call.
"""

from __future__ import annotations

import sys

from app.configs.envConfig import settings
from app.services.llm.ledger import record_call
from app.services.llm.router import model_for

_client = None


def _groq():
    global _client
    if _client is None:
        from groq import Groq

        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def chat(
    messages: list,
    max_tokens: int = 4096,
    json_mode: bool = False,
    *,
    node: str = "unknown",
) -> str:
    """
    One completion.
    """
    # Check if reGraph._chat has been patched (e.g. by runner.py cassette)
    re_graph_mod = sys.modules.get("app.services.graph.reGraph")
    if re_graph_mod is not None:
        patched_chat = getattr(re_graph_mod, "_chat", None)
        if patched_chat is not None and not getattr(patched_chat, "_is_default_facade", False):
            return patched_chat(messages, max_tokens=max_tokens, json_mode=json_mode)

    model = model_for(node)
    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": settings.LLM_TEMPERATURE,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = _groq().chat.completions.create(**kwargs)
    usage = getattr(response, "usage", None)
    record_call(
        node=node,
        model=model,
        tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
        tokens_out=getattr(usage, "completion_tokens", 0) or 0,
    )
    return response.choices[0].message.content.strip()
