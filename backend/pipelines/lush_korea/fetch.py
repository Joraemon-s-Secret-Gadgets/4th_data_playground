"""Fetch helpers for Lush Korea category pagination."""

from __future__ import annotations

import os
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup


def fetch_paginated_homepage(
    url: str,
    *,
    get_with_retries: Callable[..., Any],
    build_headers: Callable[[], dict[str, str]],
) -> str:
    """Fetch and concatenate paginated category HTML until no products remain."""
    pages: list[str] = []
    max_pages = int(os.getenv("LUSH_KR_MAX_PAGES", "20"))

    for page in range(1, max_pages + 1):
        page_url = with_page(url, page)
        response = get_with_retries(page_url, headers=build_headers(), timeout=20)
        response.raise_for_status()
        response.encoding = "utf-8"

        html = response.text
        if page > 1 and not BeautifulSoup(html, "html.parser").select("li.prdlist__item"):
            break

        pages.append(html)
        if f"page={page + 1}" not in html:
            break

    return "\n".join(pages)


def with_page(url: str, page: int) -> str:
    """Return a URL with its page query parameter set."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["page"] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

# End of file.
