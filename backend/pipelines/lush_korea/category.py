"""Category page parsing helpers for Lush Korea fragrance products."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from pipelines.common import normalize_text


BASE_URL = "https://www.lush.co.kr"
PRODUCT_TYPES = {"보디 스프레이", "바디 스프레이", "퍼퓸", "솔리드 퍼퓸", "워시 카드", "캔들"}


def extract_homepage_fragrance_products(html: str) -> list[dict[str, str]]:
    """Extract fragrance products from Lush Korea category or homepage HTML."""
    soup = BeautifulSoup(html, "html.parser")
    if products := extract_category_products(soup):
        return products

    fragrance_heading = soup.find("h2", class_="tit", string=lambda value: normalize_text(value or "") == "프래그런스")
    if fragrance_heading is None:
        return []

    section = fragrance_heading.find_parent("div", class_="swiper-slide")
    if section is None:
        return []

    products: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for caption in section.select("figcaption.txt"):
        values = [normalize_text(text) for text in caption.stripped_strings]
        values = [value for value in values if value]
        if len(values) < 2:
            continue

        product = {"korean_name": values[0], "product_type": values[1]}
        if product["product_type"] not in PRODUCT_TYPES:
            continue

        key = (product["korean_name"], product["product_type"])
        if key not in seen:
            products.append(product)
            seen.add(key)
    return products


def extract_category_products(soup: BeautifulSoup) -> list[dict[str, str]]:
    """Extract product cards from a Lush Korea category page soup."""
    products: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in soup.select("li.prdlist__item"):
        name_node = item.select_one(".prdlist__item__tit")
        type_node = item.select_one(".prdlist__item__category")
        if name_node is None or type_node is None:
            continue

        korean_name = normalize_text(name_node.get_text(" ", strip=True))
        product_type = normalize_text(type_node.get_text(" ", strip=True))
        if product_type not in PRODUCT_TYPES:
            continue

        product_url = ""
        if link := item.select_one("a[href*='/products/view/']"):
            product_url = normalize_product_url(str(link.get("href") or ""))
        regular_price = ""
        if price_node := item.select_one(".prdlist__item__price"):
            regular_price = normalize_text(price_node.get_text(" ", strip=True))
        image_url = extract_image_url(item)

        key = (korean_name, product_type)
        if key in seen:
            continue
        product = {"korean_name": korean_name, "product_type": product_type}
        if product_url:
            product["product_url"] = product_url
        if regular_price:
            product["regular_price"] = regular_price
        if image_url:
            product["image_url"] = image_url
        products.append(product)
        seen.add(key)

    return products


def normalize_product_url(href: str) -> str:
    """Normalize Lush Korea product links into canonical desktop product URLs."""
    if match := re.search(r"moveProductView\('([^']+)'", href):
        href = match.group(1)

    product_url = urljoin(BASE_URL, href).replace("/m/products/view/", "/products/view/")
    split_url = urlsplit(product_url)
    return urlunsplit((split_url.scheme, split_url.netloc, split_url.path, "", ""))


def extract_image_url(item: Any) -> str:
    """Extract the canonical product image URL from a product card."""
    image = item.select_one("img")
    if image is None:
        return ""

    for attribute in ("src", "data-src", "data-original", "data-lazy", "data-srcset", "srcset"):
        raw_value = str(image.get(attribute) or "")
        if not raw_value:
            continue
        candidate = raw_value.split(",", 1)[0].strip().split(" ", 1)[0]
        if candidate:
            return normalize_image_url(candidate)
    return ""


def normalize_image_url(src: str) -> str:
    """Normalize Lush Korea image URLs."""
    if src.startswith("//"):
        src = f"https:{src}"
    return urljoin(BASE_URL, src)


def format_korean_product_name(korean_name: str, product_type: str) -> str:
    """Append product type to the Korean display name when it is missing."""
    if korean_name.endswith(product_type):
        return korean_name
    return normalize_text(f"{korean_name} {product_type}")

# End of file.
