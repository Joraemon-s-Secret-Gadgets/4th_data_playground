"""Fetch helpers for Chanel Korea category pagination."""

from __future__ import annotations

import os
from collections.abc import Callable

from pipelines.chanel_korea.category import extract_fragrance_products


def fetch_paginated_category(
    url: str,
    *,
    fetch_page: Callable[[str], str],
) -> str:
    """Fetch and concatenate Chanel Korea category pages."""
    pages: list[str] = []
    max_pages = int(os.getenv("CHANEL_KR_MAX_PAGES", "6"))

    for page in range(1, max_pages + 1):
        page_url = with_page(url, page)
        html = fetch_page(page_url)
        if page > 1 and not extract_fragrance_products(html):
            break
        pages.append(html)

    return "\n".join(pages)


def with_page(url: str, page: int) -> str:
    """Return a Chanel Korea category URL for a page number."""
    if page <= 1:
        return url
    return f"{url.rstrip('/')}/page-{page}/"

# End of file.
