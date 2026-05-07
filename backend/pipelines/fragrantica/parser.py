"""HTML parsing helpers refactored from Fragrantica brand crawlers."""

from __future__ import annotations

import html as ihtml
import re
from typing import Any


FORBIDDEN_TEXT = [
    "100% Free - Always",
    "Create Free Account",
    "Already have an account? Log in",
    "Continue browsing",
]


def clean_text(value: str) -> str:
    """Strip scripts, tags, and known Fragrantica account prompts from text."""
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", value or "", flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = ihtml.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    for forbidden in FORBIDDEN_TEXT:
        text = text.replace(forbidden, "").strip()
    return text


def parse_perfume(url: str, page_html: str, brand: str) -> dict[str, Any]:
    """Parse one Fragrantica perfume page into the source crawler row shape."""
    description = extract_description_text(page_html)
    top_notes = extract_notes_level(page_html, "top")
    middle_notes = extract_notes_level(page_html, "middle")
    base_notes = extract_notes_level(page_html, "base")

    if not (top_notes and middle_notes and base_notes):
        fallback = split_note_sentence(description)
        top_notes = top_notes or fallback["top"]
        middle_notes = middle_notes or fallback["middle"]
        base_notes = base_notes or fallback["base"]

    if not top_notes and not middle_notes and not base_notes:
        base_notes = extract_feature_notes(description)

    return {
        "brand": brand,
        "name": extract_name(page_html, url, brand),
        "release_year": extract_year(description),
        "accords": "; ".join(extract_accords(page_html)),
        "top_notes": "; ".join(top_notes),
        "middle_notes": "; ".join(middle_notes),
        "base_notes": "; ".join(base_notes),
        "_url": url,
    }


def extract_name(page_html: str, url: str, brand: str) -> str:
    """Extract a Fragrantica perfume name from itemprop heading or URL slug."""
    match = re.search(r"<h1[^>]*itemprop=[\"']name[\"'][^>]*>([\s\S]*?)</h1>", page_html, re.I)
    if match:
        text = clean_text(match.group(1))
        text = re.sub(r"\s+for\s+(women|men|women and men|men and women)\s*$", "", text, flags=re.I).strip()
        text = re.sub(r"\s+" + re.escape(brand).replace(r"\ ", r"\s+") + r"\s*$", "", text, flags=re.I).strip()
        text = re.sub(r"\s+by\s+" + re.escape(brand).replace(r"\ ", r"\s+") + r"\s*$", "", text, flags=re.I).strip()
        if text:
            return text

    slug = url.rsplit("/", 1)[-1].replace(".html", "")
    slug = re.sub(r"-\d+$", "", slug)
    return slug.replace("-", " ")


def extract_description_text(page_html: str) -> str:
    """Extract Fragrantica description text used for fallback note parsing."""
    match = re.search(
        r"<div[^>]+id=[\"']perfume-description-content[\"'][^>]*>([\s\S]*?)(?:<pyramid-level-new|</section>|</article>)",
        page_html,
        re.I,
    )
    if match:
        return clean_text(match.group(1))
    return clean_text(page_html[:300000])


def extract_year(description: str) -> str:
    """Extract launch year from Fragrantica description prose."""
    for pattern in [
        r"was launched in\s+(\d{4})",
        r"were launched in\s+(\d{4})",
        r"launched in\s+(\d{4})",
        r"introduced in\s+(\d{4})",
    ]:
        match = re.search(pattern, description, re.I)
        if match:
            return match.group(1)

    match = re.search(r"\b(19\d{2}|20\d{2})\b", description[:1200])
    return match.group(1) if match else ""


def extract_accords(page_html: str) -> list[str]:
    """Extract main accord names from a Fragrantica page segment."""
    index = page_html.lower().find("main accords")
    if index == -1:
        return []

    end_candidates = [
        position
        for position in [
            page_html.find("perfume-description-content", index),
            page_html.find("<pyramid-level-new", index),
        ]
        if position != -1
    ]
    end = min(end_candidates) if end_candidates else index + 20000
    segment = page_html[index:end]
    values = [
        clean_text(value)
        for value in re.findall(
            r"<span[^>]*class=[\"'][^\"']*\btruncate\b[^\"']*[\"'][^>]*>([\s\S]*?)</span>",
            segment,
            re.I,
        )
    ]
    return _unique(value for value in values if value and value.lower() != "main accords")


def extract_notes_level(page_html: str, level: str) -> list[str]:
    """Extract top/middle/base notes from pyramid-level-new elements."""
    match = re.search(
        r"<pyramid-level-new\s+notes=[\"']" + re.escape(level) + r"[\"'][^>]*>([\s\S]*?)</pyramid-level-new>",
        page_html,
        re.I,
    )
    if not match:
        return []

    segment = match.group(1)
    values = [
        clean_text(value)
        for value in re.findall(
            r"<span[^>]*class=[\"'][^\"']*pyramid-note-label[^\"']*[\"'][^>]*>([\s\S]*?)</span>",
            segment,
            re.I,
        )
    ]
    if not values:
        values = [ihtml.unescape(value).strip() for value in re.findall(r"alt=[\"']([^\"']+)[\"']", segment, re.I)]

    return _unique(value for value in values if value)


def split_note_sentence(description: str) -> dict[str, list[str]]:
    """Parse prose patterns that list top, middle, and base notes."""
    result = {"top": [], "middle": [], "base": []}
    patterns = [
        r"Top notes? (?:are|is) (.*?);\s*middle notes? (?:are|is) (.*?);\s*base notes? (?:are|is) (.*?)(?:\.|$)",
        r"Top notes?:? (.*?);\s*Middle notes?:? (.*?);\s*Base notes?:? (.*?)(?:\.|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, description, re.I)
        if not match:
            continue
        for key, value in zip(["top", "middle", "base"], match.groups()):
            result[key] = [part.strip() for part in re.split(r",| and ", value) if part.strip()]
        break
    return result


def extract_feature_notes(description: str) -> list[str]:
    """Extract generic feature notes when note pyramid fields are absent."""
    patterns = [
        r"The fragrance features\s+(.*?)(?:\.|$)",
        r"features\s+(.*?)(?:\.|$)",
        r"notes include\s+(.*?)(?:\.|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, description, re.I)
        if match:
            return [part.strip() for part in re.split(r",| and ", match.group(1)) if part.strip()]
    return []


def _unique(values: object) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and not any(forbidden in value for forbidden in FORBIDDEN_TEXT) and value not in result:
            result.append(value)
    return result

# End of file.
