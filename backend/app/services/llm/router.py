"""
Which model runs which node.

The plan's split: a cheap router model for intake, classification and structural
checks; a drafter-class model for the writing. Encoding it as a table rather than
a constant means changing one node's model is a one-line diff a reviewer can see,
not a search through the graph.

Today every node resolves to the router model, because that is what the
prototype used and S10's contract is that the split changes no behaviour. The
table is the mechanism; S15 is where the drafting nodes move.
"""

from __future__ import annotations

from app.configs.envConfig import settings

# node -> setting name. Resolved at call time so a deployment can change a model
# without a code change.
_ASSIGNMENT: dict[str, str] = {
    "intake": "ROUTER_MODEL",
    "research": "ROUTER_MODEL",
    "valuation_structure": "ROUTER_MODEL",
    "valuation_critic": "ROUTER_MODEL",
    "section_drafter": "ROUTER_MODEL",
    "compliance_structure": "ROUTER_MODEL",
    "compliance_critic": "ROUTER_MODEL",
    "compliance_drafter": "ROUTER_MODEL",
    "agreement_drafter": "ROUTER_MODEL",
    "healer": "ROUTER_MODEL",
}

DEFAULT_SETTING = "ROUTER_MODEL"


def model_for(node: str) -> str:
    return getattr(settings, _ASSIGNMENT.get(node, DEFAULT_SETTING))


def assignments() -> dict[str, str]:
    """Node -> resolved model name. Used by the ledger test and by `/usage`."""
    return {node: model_for(node) for node in _ASSIGNMENT}
