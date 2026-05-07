"""Detail and review parsers for Fraganty perfume pages."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from pipelines.common import normalize_text
from pipelines.fraganty.category import perfume_name_from_url


NOTE_LABELS = {"Top": "Top Notes", "Heart": "Heart Notes", "Base": "Base Notes"}


def extract_perfume_detail(html: str, *, brand: str, url: str) -> dict[str, Any]:
    """Extract raw Fraganty perfume detail fields from product HTML."""
    soup = BeautifulSoup(html, "html.parser")
    name = _extract_heading_name(soup) or perfume_name_from_url(url)

    return {
        "brand": brand,
        "url": url,
        "name": _strip_brand_from_name(name, brand),
        "image_url": _extract_image_url(soup),
        "main_accords": _extract_main_accords(soup),
        "notes": _extract_notes(soup),
        "usage_stats": _extract_usage_stats(soup),
        "first_impression": "N/A",
        "scent_profile": "N/A",
        "status": "Success",
    }


def extract_review_detail(html: str) -> dict[str, str]:
    """Extract review prose from a Fraganty review page."""
    soup = BeautifulSoup(html, "html.parser")
    return {
        "first_impression": _extract_paragraph_section(soup, "First Impression") or "N/A",
        "scent_profile": _extract_paragraph_section(soup, "Scent Profile") or "N/A",
    }


def _extract_heading_name(soup: BeautifulSoup) -> str:
    if heading := soup.find("h1"):
        return normalize_text(heading.get_text(" ", strip=True)).lower()
    return ""


def _strip_brand_from_name(name: str, brand: str) -> str:
    value = normalize_text(name).lower()
    brand_value = brand.strip().lower()
    if brand_value and value.startswith(brand_value):
        value = value[len(brand_value) :].strip()
    return value


def _extract_image_url(soup: BeautifulSoup) -> str:
    image = soup.select_one(".perfume-img-bg img[src], img[src*='img.fraganty.ai']")
    if image is None:
        return "N/A"
    return str(image.get("src") or "N/A")


def _extract_main_accords(soup: BeautifulSoup) -> list[dict[str, str]]:
    heading = _find_heading(soup, "Main Accords")
    if heading is None:
        return []

    container = heading.find_next("div")
    if container is None:
        return []

    accords: list[dict[str, str]] = []
    for node in container.find_all("a", class_="group"):
        name_node = node.find("span", class_="w-24")
        percent_node = node.find("span", class_="tabular-nums")
        if name_node is None:
            continue
        accord = normalize_text(name_node.get_text(" ", strip=True))
        if not accord:
            continue
        accords.append(
            {
                "accord": accord,
                "percentage": normalize_text(percent_node.get_text(" ", strip=True)) if percent_node else "",
            }
        )
    return accords


def _extract_notes(soup: BeautifulSoup) -> dict[str, list[str]]:
    notes: dict[str, list[str]] = {"Top": [], "Heart": [], "Base": []}
    for key, label in NOTE_LABELS.items():
        label_node = soup.find("span", string=lambda value: bool(value and label in value))
        if label_node is None:
            continue
        parent = label_node.find_parent("div")
        container = parent.find_next_sibling("div") if parent else None
        if container is None:
            container = label_node.find_next("div")
        if container is None:
            continue
        notes[key] = [
            normalize_text(node.get_text(" ", strip=True))
            for node in container.select("span.flex-1")
            if normalize_text(node.get_text(" ", strip=True))
        ]
    return notes


def _extract_usage_stats(soup: BeautifulSoup) -> dict[str, dict[str, str]]:
    usage: dict[str, dict[str, str]] = {}

    season_heading = soup.find(lambda tag: isinstance(tag, Tag) and "Best Season" in tag.get_text(" ", strip=True))
    season_grid = season_heading.find_next("div", class_="grid-cols-4") if season_heading else None
    if season_grid:
        usage["Season"] = _zip_percentages(["Winter", "Spring", "Summer", "Fall"], season_grid)

    time_heading = soup.find(lambda tag: isinstance(tag, Tag) and "Day & Night" in tag.get_text(" ", strip=True))
    time_grid = time_heading.find_next("div", class_="grid-cols-2") if time_heading else None
    if time_grid:
        usage["Time"] = _zip_percentages(["Day", "Night"], time_grid)

    return usage


def _zip_percentages(labels: list[str], container: Tag) -> dict[str, str]:
    values = [normalize_text(node.get_text(" ", strip=True)) for node in container.find_all("p", class_="font-semibold")]
    return {label: value for label, value in zip(labels, values) if value}


def _extract_paragraph_section(soup: BeautifulSoup, title: str) -> str:
    heading = soup.find(
        lambda tag: isinstance(tag, Tag)
        and tag.name in {"h2", "h3"}
        and re.search(title, tag.get_text(" ", strip=True), re.I)
    )
    if heading is None:
        return ""

    paragraphs: list[str] = []
    current = heading.find_next_sibling()
    while isinstance(current, Tag) and current.name == "p":
        text = normalize_text(current.get_text(" ", strip=True).replace("''", "'"))
        if text:
            paragraphs.append(text)
        current = current.find_next_sibling()
    return "\n".join(paragraphs)


def _find_heading(soup: BeautifulSoup, text: str) -> Tag | None:
    return soup.find(
        lambda tag: isinstance(tag, Tag) and tag.name in {"h2", "h3"} and text in tag.get_text(" ", strip=True)
    )

# End of file.
