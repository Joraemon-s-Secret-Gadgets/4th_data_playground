"""Category page parsing helpers for Chanel Korea fragrance products."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from pipelines.common import normalize_text


BASE_URL = "https://www.chanel.com"
PRODUCT_TYPE_PATTERNS = (
    "오 드 빠르펭",
    "오 드 퍼퓸",
    "오 드 뚜왈렛",
    "오 드 코롱",
    "빠르펭",
    "퍼퓸",
)
NON_FRAGRANCE_PATTERNS = (
    "바디 오일",
    "모이스춰라이징",
    "로션",
    "리퀴드 솝",
    "바디 크림",
    "헤어 미스트",
    "립 듀오",
)


def extract_fragrance_products(html: str) -> list[dict[str, str]]:
    """Extract Chanel Korea fragrance products from category HTML."""
    soup = BeautifulSoup(html, "html.parser")
    products: list[dict[str, str]] = []
    seen: set[str] = set()

    for link in soup.select('a[href*="/kr/fragrance/p/"]'):
        text = normalize_text(link.get_text(" ", strip=True))
        if not text:
            continue

        product = extract_product_summary(text)
        if product is None:
            continue

        product_url = normalize_product_url(str(link.get("href") or ""))
        if not product_url or product_url in seen:
            continue

        card_text = normalize_text((link.find_parent(["article", "li"]) or link).get_text(" ", strip=True))
        card = link.find_parent(["article", "li", "div"]) or link
        price = extract_price(card_text) or extract_price(text)

        products.append(
            {
                "country": "KR",
                "brand": "CHANEL",
                "korean_name": product["korean_name"],
                "english_name": extract_english_name(product_url),
                "product_type": product["product_type"],
                "product_url": product_url,
                "regular_price": price,
                "image_url": extract_image_url(card),
            }
        )
        seen.add(product_url)

    return products


def extract_product_summary(text: str) -> dict[str, str] | None:
    """Extract name and product type from a Chanel category card label."""
    normalized = normalize_text(text)
    match = re.search(r"(.+?)\s+레퍼런스\s+([A-Za-z0-9]+)", normalized)
    if not match:
        return None

    korean_name = normalize_text(match.group(1))
    if any(pattern in korean_name for pattern in NON_FRAGRANCE_PATTERNS):
        return None

    product_type = infer_product_type(korean_name)
    if not product_type:
        return None

    return {"korean_name": korean_name, "product_type": product_type}


def infer_product_type(korean_name: str) -> str:
    """Infer the fragrance type from a Korean Chanel product name."""
    for pattern in PRODUCT_TYPE_PATTERNS:
        if pattern in korean_name:
            return pattern
    return ""


def extract_price(text: str) -> str:
    """Extract a KRW display price from card text."""
    if match := re.search(r"\d{1,3}(?:,\d{3})+\s*원(?:\s*부터)?", normalize_text(text)):
        return normalize_text(match.group(0))
    return ""


def normalize_product_url(href: str) -> str:
    """Normalize Chanel Korea product URLs."""
    product_url = urljoin(BASE_URL, href)
    split_url = urlsplit(product_url)
    return urlunsplit((split_url.scheme, split_url.netloc, split_url.path.rstrip("/"), "", ""))


def extract_english_name(product_url: str) -> str:
    """Extract a readable English product name from a Chanel product URL."""
    slug = product_url.rstrip("/").rsplit("/", 1)[-1]
    if not slug:
        return ""
    replacements = {
        "n5": "N°5",
        "n1": "N°1",
    }
    words = [replacements.get(word, word.capitalize()) for word in slug.split("-") if word]
    return normalize_text(" ".join(words))


def extract_image_url(card: Any) -> str:
    """Extract the first product image URL from a Chanel product card."""
    for node in card.select("source[srcset], img[src], img[data-src], img[data-lazy-src]"):
        raw_value = str(
            node.get("srcset")
            or node.get("src")
            or node.get("data-src")
            or node.get("data-lazy-src")
            or ""
        )
        if not raw_value:
            continue
        if node.get("srcset"):
            candidate = re.split(r",\s+", raw_value, maxsplit=1)[0].strip().split(" ", 1)[0]
        else:
            candidate = raw_value.strip()
        if candidate:
            return normalize_asset_url(candidate)
    return ""


def normalize_asset_url(src: str) -> str:
    """Normalize Chanel asset URLs."""
    if src.startswith("//"):
        src = f"https:{src}"
    return urljoin(BASE_URL, src)

# End of file.
