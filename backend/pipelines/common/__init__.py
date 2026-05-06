"""Shared scraping utilities used by country-specific Lush pipelines."""

from pipelines.common.browser import fetch_rendered_html
from pipelines.common.http import build_request_headers, get_with_retries
from pipelines.common.output import print_json_rows
from pipelines.common.reviews import extract_product_remote_id, normalize_review
from pipelines.common.text import normalize_text, strip_tags

__all__ = [
    "build_request_headers",
    "extract_product_remote_id",
    "fetch_rendered_html",
    "get_with_retries",
    "normalize_review",
    "normalize_text",
    "print_json_rows",
    "strip_tags",
]

# End of file.
