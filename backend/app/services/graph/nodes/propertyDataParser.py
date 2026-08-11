"""
Property data parser node.
"""

from __future__ import annotations

from app.services.graph.state import REState, safe
from app.services.ingest.propertyDataParser import parse_property_data
from app.services.ingest.result import MalformedInputError, UnrecognisedFormatError

_EMPTY_PARSE = {
    "format": "empty",
    "records": [],
    "rejected": [],
    "counts": {"input": 0, "parsed": 0, "rejected": 0, "duplicate": 0},
    "metadata": {},
}


def property_data_parser_node(state: REState) -> dict:
    raw = safe(state, "raw_property_data", "")
    if not raw:
        return {"parsed_data": dict(_EMPTY_PARSE)}

    try:
        result = parse_property_data(raw)
    except (UnrecognisedFormatError, MalformedInputError) as e:
        unparseable = {**_EMPTY_PARSE, "format": "unparseable", "metadata": {"error": str(e)}}
        return {
            "parsed_data": unparseable,
            "generation_errors": f"property data could not be parsed: {e}",
        }

    return {"parsed_data": result.to_dict()}
