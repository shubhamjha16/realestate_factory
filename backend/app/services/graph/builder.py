"""
Graph builder — pure structural wiring of the StateGraph.

Zero prompt text. All node logic, prompts, and routing rules live in dedicated
submodules in `nodes/`, `prompts/`, and `routes.py`.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.services.graph.nodes.agreementDrafter import agreement_drafter_node
from app.services.graph.nodes.complianceCritic import compliance_critic_node
from app.services.graph.nodes.complianceDrafter import compliance_drafter_node
from app.services.graph.nodes.complianceStructure import compliance_structure_node
from app.services.graph.nodes.evidenceCheck import evidence_check_node
from app.services.graph.nodes.evidenceScan import evidence_scan_node
from app.services.graph.nodes.healer import healer_node
from app.services.graph.nodes.intake import intake_node
from app.services.graph.nodes.propertyDataParser import property_data_parser_node
from app.services.graph.nodes.recRenderer import rec_renderer_node
from app.services.graph.nodes.renderer import renderer_node
from app.services.graph.nodes.research import research_node
from app.services.graph.nodes.sectionDrafter import section_drafter_node
from app.services.graph.nodes.upload import upload_node
from app.services.graph.nodes.valuationCalculator import valuation_calculator_node
from app.services.graph.nodes.valuationCritic import valuation_critic_node
from app.services.graph.nodes.valuationStructure import valuation_structure_node
from app.services.graph.nodes.vision import vision_node
from app.services.graph.routes import (
    compliance_critic_route,
    evidence_scan_route,
    gated_route,
    renderer_route,
    section_drafter_route,
    valuation_critic_route,
)
from app.services.graph.state import REState


def build_graph():
    """Construct and compile the RE StateGraph pipeline."""
    g = StateGraph(REState)

    # Nodes
    g.add_node("intake", intake_node)
    g.add_node("property_data_parser", property_data_parser_node)
    g.add_node("valuation_calculator", valuation_calculator_node)
    g.add_node("research", research_node)
    g.add_node("vision", vision_node)
    g.add_node("evidence_check", evidence_check_node)
    g.add_node("evidence_scan", evidence_scan_node)
    g.add_node("rec_renderer", rec_renderer_node)
    g.add_node("valuation_structure", valuation_structure_node)
    g.add_node("valuation_critic", valuation_critic_node)
    g.add_node("section_drafter", section_drafter_node)
    g.add_node("compliance_structure", compliance_structure_node)
    g.add_node("compliance_critic", compliance_critic_node)
    g.add_node("compliance_drafter", compliance_drafter_node)
    g.add_node("agreement_drafter", agreement_drafter_node)
    g.add_node("renderer", renderer_node)
    g.add_node("healer", healer_node)
    g.add_node("upload", upload_node)

    # Edges & Routing
    g.set_entry_point("intake")
    g.add_edge("intake", "property_data_parser")
    g.add_edge("property_data_parser", "valuation_calculator")
    g.add_edge("valuation_calculator", "research")
    g.add_edge("research", "vision")

    g.add_edge("vision", "evidence_check")
    g.add_conditional_edges("evidence_check", gated_route, {
        "blocked": END,
        "rec_renderer": "rec_renderer",
        "valuation_structure": "valuation_structure",
        "compliance_structure": "compliance_structure",
        "agreement_drafter": "agreement_drafter",
    })

    g.add_edge("rec_renderer", "evidence_scan")

    g.add_edge("valuation_structure", "valuation_critic")
    g.add_conditional_edges("valuation_critic", valuation_critic_route, {
        "valuation_structure": "valuation_structure",
        "section_drafter": "section_drafter",
    })
    g.add_conditional_edges("section_drafter", section_drafter_route, {
        "section_drafter": "section_drafter",
        "renderer": "evidence_scan",
    })

    g.add_edge("compliance_structure", "compliance_critic")
    g.add_conditional_edges("compliance_critic", compliance_critic_route, {
        "compliance_structure": "compliance_structure",
        "compliance_drafter": "compliance_drafter",
    })
    g.add_edge("compliance_drafter", "evidence_scan")

    g.add_edge("agreement_drafter", "evidence_scan")

    g.add_conditional_edges("evidence_scan", evidence_scan_route, {
        "blocked": END,
        "renderer": "renderer",
    })

    g.add_conditional_edges("renderer", renderer_route, {
        "healer": "healer",
        "upload": "upload",
    })
    g.add_edge("healer", "renderer")
    g.add_edge("upload", END)

    return g.compile()


app = build_graph()
