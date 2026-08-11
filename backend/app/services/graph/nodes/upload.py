"""
Upload node.
"""

from __future__ import annotations

from app.services.graph.state import REState
from app.services.storage.uploader import upload


def upload_node(state: REState) -> dict:
    doc_path = state.get("doc_path")
    if not doc_path:
        return {"doc_url": None, "generation_errors": "No document generated"}
    try:
        url = upload(doc_path)
        return {"doc_url": url, "generation_errors": None}
    except Exception as e:
        return {"doc_url": f"file://{doc_path}", "generation_errors": str(e)}
