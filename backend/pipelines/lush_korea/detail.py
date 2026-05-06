"""Product detail parsing helpers for Lush Korea product pages."""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from pipelines.common import normalize_text


def extract_product_detail(html: str) -> dict[str, Any]:
    """Extract full ingredients and key ingredients from product detail HTML."""
    soup = BeautifulSoup(html, "html.parser")
    ingredient_section = _find_ingredient_section(soup)
    if ingredient_section is None:
        return _extract_product_detail_from_all_ingredient_block(soup)

    ingredients = ""
    for text_block in ingredient_section.select("p.text__main"):
        label = text_block.select_one(".theme__gray900")
        if label is None or "전 성분" not in normalize_text(label.get_text(" ", strip=True)):
            continue

        value = text_block.select_one(".theme__gray800")
        if value is not None:
            ingredients = normalize_text(value.get_text(" ", strip=True))
            break

    key_ingredients: list[str] = []
    seen: set[str] = set()
    for node in ingredient_section.select(".ingredient .ingredient__name"):
        name = normalize_text(node.get_text(" ", strip=True))
        if name and name not in seen:
            key_ingredients.append(name)
            seen.add(name)

    if not ingredients:
        fallback = _extract_product_detail_from_all_ingredient_block(soup)
        ingredients = fallback["ingredients"]
        key_ingredients = key_ingredients or fallback["key_ingredients"]

    return {"ingredients": ingredients, "key_ingredients": key_ingredients}


def _extract_product_detail_from_all_ingredient_block(soup: BeautifulSoup) -> dict[str, Any]:
    ingredients = ""
    key_ingredients: list[str] = []

    for text_block in soup.select(".all-ingre p"):
        label = text_block.find("strong")
        if label is None:
            continue

        label_text = normalize_text(label.get_text(" ", strip=True))
        value = _remove_leading_label(text_block.get_text(" ", strip=True), label_text)
        if "전 성분" in label_text and value:
            ingredients = value
        elif "대표성분" in label_text and value:
            key_ingredients = [name for name in (normalize_text(part) for part in value.split(",")) if name]

    return {"ingredients": ingredients, "key_ingredients": key_ingredients}


def _remove_leading_label(text: str, label: str) -> str:
    normalized_text = normalize_text(text)
    normalized_label = normalize_text(label)
    if normalized_text.startswith(normalized_label):
        return normalize_text(normalized_text[len(normalized_label) :])
    return normalized_text


def _find_ingredient_section(soup: BeautifulSoup) -> Any | None:
    heading = soup.find(string=lambda value: normalize_text(value or "") == "INGREDIENT")
    if heading is None:
        return None

    heading_node = heading.parent
    if heading_node is None:
        return None
    return heading_node.find_parent("div", class_="primary__article")

# End of file.
