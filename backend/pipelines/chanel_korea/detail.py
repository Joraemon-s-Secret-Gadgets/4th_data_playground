"""Product detail parsing helpers for Chanel Korea product pages."""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from pipelines.common import normalize_text
from pipelines.chanel_korea.category import normalize_asset_url


DETAIL_STOP_HEADINGS = {
    "상품 필수 정보",
    "성분 목록",
    "제품 주요 사양",
    "사용기한",
    "책임판매업자",
    "제조국",
    "기능성 화장품 심사필여부",
    "사용시 주의사항",
    "품질보증기준",
    "소비자상담 전화번호",
}


def extract_product_detail(html: str) -> dict[str, Any]:
    """Extract ingredients and composition notes from a Chanel product page."""
    text_lines = _text_lines(html)
    soup = BeautifulSoup(html, "html.parser")
    return {
        "ingredients": _extract_section_value(text_lines, "성분 목록"),
        "key_ingredients": _extract_key_ingredients(text_lines),
        "image_url": _extract_image_url(soup),
    }


def _extract_key_ingredients(text_lines: list[str]) -> list[str]:
    composition = _extract_section_value(text_lines, "구성")
    return [composition] if composition else []


def _extract_section_value(text_lines: list[str], heading: str) -> str:
    for index, line in enumerate(text_lines):
        if line != heading:
            continue

        values: list[str] = []
        for candidate in text_lines[index + 1 :]:
            if candidate in DETAIL_STOP_HEADINGS or candidate.startswith("성분 목록은"):
                break
            if candidate.startswith("설명(") or candidate.endswith("(으)로 돌아가기"):
                break
            if candidate.startswith("####"):
                break
            if candidate and candidate != heading:
                values.append(candidate)

        return normalize_text(" ".join(values))

    return ""


def _text_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [normalize_text(line) for line in soup.get_text("\n", strip=True).splitlines() if normalize_text(line)]


def _extract_image_url(soup: BeautifulSoup) -> str:
    for selector in ('meta[property="og:image"]', 'meta[name="twitter:image"]'):
        if node := soup.select_one(selector):
            if content := str(node.get("content") or ""):
                return normalize_asset_url(content)
    return ""

# End of file.
