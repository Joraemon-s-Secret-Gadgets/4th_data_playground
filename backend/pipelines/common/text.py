"""Text normalization helpers shared by scraper parsers."""

from __future__ import annotations

import re
from html import unescape


def normalize_text(value: str) -> str:
    """Collapse repeated whitespace and trim surrounding spaces."""
    return re.sub(r"\s+", " ", value).strip()


def strip_tags(value: str) -> str:
    """Remove simple HTML tags and normalize the resulting text."""
    return normalize_text(re.sub(r"<[^>]+>", "", unescape(value)))

# End of file.
