"""Category page parsing helpers for Jo Malone Korea fragrance products."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from pipelines.common import normalize_text


BASE_URL = "https://www.jomalone.co.kr"


def extract_fragrance_products(html: str) -> list[dict[str, str]]:
    """Extract fragrance product cards from a Jo Malone Korea category page."""
    soup = BeautifulSoup(html, "html.parser")
    products: list[dict[str, str]] = []
    seen: set[str] = set()

    for card in soup.select(".elc-grid-item-product"):
        link = card.select_one('a[href*="/product/"]')
        name_node = card.select_one('[data-test-id="product_name"], .js-product-display-name-link, h2')
        if link is None or name_node is None:
            continue

        product_url = normalize_product_url(str(link.get("href") or ""))
        english_name = normalize_text(name_node.get_text(" ", strip=True))
        product_type = infer_product_type(english_name, product_url)
        if not product_url or not english_name or not product_type:
            continue
        if product_url in seen:
            continue

        product = {
            "country": "KR",
            "korean_name": "",
            "english_name": english_name,
            "product_type": product_type,
            "product_url": product_url,
            "regular_price": "",
            "image_url": extract_image_url(card),
        }
        if size := extract_size(card):
            product["size"] = size

        products.append(product)
        seen.add(product_url)

    return products


def infer_product_type(english_name: str, product_url: str = "") -> str:
    """Infer the normalized Jo Malone fragrance type from a name or URL."""
    value = f"{english_name} {product_url}".lower()
    if "cologne intense" in value:
        return "코롱 인텐스"
    if "cologne" in value and ("/colognes/" in value or "/private/" in value):
        return "코롱"
    return ""


def extract_size(card: BeautifulSoup) -> str:
    """Extract the display size from a product card."""
    if size_node := card.select_one(".js-size"):
        return normalize_text(size_node.get_text(" ", strip=True))
    return ""


def extract_image_url(card: BeautifulSoup) -> str:
    """Extract the first product image URL from a product card."""
    for node in card.select("source[srcset], img[src], img[data-src]"):
        raw_value = str(node.get("srcset") or node.get("src") or node.get("data-src") or "")
        if not raw_value:
            continue
        candidate = raw_value.split(",", 1)[0].strip().split(" ", 1)[0]
        if candidate:
            return normalize_asset_url(candidate)
    return ""


def normalize_product_url(href: str) -> str:
    """Normalize Jo Malone Korea product links."""
    product_url = urljoin(BASE_URL, href)
    split_url = urlsplit(product_url)
    return urlunsplit((split_url.scheme, split_url.netloc, split_url.path.rstrip("/"), "", ""))


def normalize_asset_url(src: str) -> str:
    """Normalize Jo Malone Korea asset URLs."""
    if src.startswith("//"):
        src = f"https:{src}"
    return urljoin(BASE_URL, src)


def format_price_krw(value: object) -> str:
    """Format a numeric KRW value as a Korean display price."""
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d]", "", value)
        if not cleaned:
            return ""
        value = int(cleaned)
    if not isinstance(value, (int, float)):
        return ""
    return f"{int(value):,}원"

# End of file.
