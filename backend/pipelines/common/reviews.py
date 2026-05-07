"""Review and product identifier normalization helpers."""

from __future__ import annotations

import re
from typing import Any

from pipelines.common.text import normalize_text


def extract_product_remote_id(product_url: str) -> str:
    """Extract the review provider's product identifier from a Lush URL."""
    if match := re.search(r"/products/view/([^/?#]+)", product_url):
        return match.group(1)
    if match := re.search(r"/(\d+)(?:[/?#]|$)", product_url):
        return match.group(1)
    return ""


def normalize_review(review: dict[str, Any]) -> dict[str, Any]:
    """Normalize review payload fields used by downstream data files."""
    return {
        "id": review.get("id"),
        "title": normalize_text(str(review.get("title") or "")),
        "text": normalize_text(str(review.get("text") or "")),
        "rating": review.get("rating"),
        "created_at": str(review.get("created_at") or ""),
        "user_nickname": str(review.get("user_nickname") or ""),
        "helpful_count": review.get("helpful_count") or 0,
        "selected_options": review.get("selected_options") or [],
        "media_count": review.get("media_count") or 0,
    }

# End of file.
