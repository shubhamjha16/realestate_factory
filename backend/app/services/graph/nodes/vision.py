"""
Vision node for generating report header image.
"""

from __future__ import annotations

from app.configs.envConfig import settings
from app.services.graph.state import REState, safe


def vision_node(state: REState) -> dict:
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.ImageGenerationModel("imagen-3.0-generate-002")  # type: ignore[attr-defined]
        client = safe(state, "client_name", "RealEstate")
        result = model.generate_images(
            prompt=(
                f"Professional real estate valuation report letterhead for {client}, "
                "navy blue and gold, property icon, clean corporate style, white background"
            ),
            number_of_images=1, aspect_ratio="16:1",
        )
        img_path = f"/tmp/{state['_job_id']}_header.png"
        result.images[0].save(img_path)
        return {"header_image_path": img_path}
    except Exception:
        return {"header_image_path": None}
