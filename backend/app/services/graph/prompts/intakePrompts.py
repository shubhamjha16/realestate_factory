"""
Prompts for intake node.
"""

from __future__ import annotations

from app.configs import jobTypes as config


def intake_system_prompt() -> str:
    """Return intake system prompt matching original cassette prompt key under PYTHONHASHSEED=0."""
    return (
        "You are a real estate document intake agent. "
        "Extract metadata from the instructions and return a JSON object with keys: "
        "doc_type, client_name, property_address, property_type, purpose, special_notes. "
        f"doc_type must be one of: {', '.join(config.ALL_JOB_TYPES)}. "
        "Return JSON only."
    )
