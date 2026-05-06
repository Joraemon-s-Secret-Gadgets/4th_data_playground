"""Category and fallback HTML parsers for Lush UK fragrance products."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from pipelines.common import normalize_text
from pipelines.lush_uk.search import PRODUCT_TYPES


BASE_URL = "https://www.lush.com"


def scrape_perfume_names_from_html(html: str) -> list[dict[str, str]]:
    """Extract normalized fragrance rows from Lush UK category HTML."""
    raise_if_cloudflare_challenge(html)
    return [
        {
            "country": "UK",
            "english_name": product["english_name"],
            "product_type": product["product_type"],
            "product_url": product["product_url"],
        }
        for product in extract_fragrance_products(html)
    ]


def extract_fragrance_products(html: str) -> list[dict[str, str]]:
    """Extract product links from rendered category HTML."""
    soup = BeautifulSoup(html, "html.parser")
    products: list[dict[str, str]] = []
    seen: set[str] = set()

    for link in soup.select('a[href*="/uk/en/p/"]'):
        product_url = normalize_product_url(link["href"])
        if product_url in seen:
            continue

        card_text = product_card_text(link)
        product_type = infer_product_type(card_text, product_url)
        if not product_type:
            continue
        english_name = infer_product_name(card_text, product_type, product_url)
        if not english_name:
            continue
        image_url = extract_image_url(link)

        product = {
            "english_name": english_name,
            "product_type": product_type,
            "product_url": product_url,
        }
        if image_url:
            product["image_url"] = image_url
        products.append(product)
        seen.add(product_url)

    return products or extract_referenced_products(html)


def extract_referenced_products(html: str) -> list[dict[str, str]]:
    """Extract referenced products from Next.js Apollo state when links are absent."""
    soup = BeautifulSoup(html, "html.parser")
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data is None or next_data.string is None:
        return []

    payload = json.loads(next_data.string)
    apollo_state = payload.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
    products: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in apollo_state.values():
        if not isinstance(item, dict) or item.get("__typename") != "AttributeValue":
            continue
        if not str(item.get("reference") or "").startswith("UHJvZHVjdD"):
            continue

        product_type = infer_referenced_product_type(str(item.get("slug") or ""))
        if not product_type:
            continue

        english_name = normalize_text(str(item.get("name") or ""))
        if not english_name:
            continue

        key = (english_name, product_type)
        if key in seen:
            continue
        products.append(
            {
                "english_name": english_name,
                "product_type": product_type,
                "product_url": build_product_url(english_name, product_type),
            }
        )
        seen.add(key)

    return products


def raise_if_cloudflare_challenge(html: str) -> None:
    """Raise when the response is a Cloudflare challenge instead of content."""
    lowered = html.lower()
    if (
        ("just a moment" in lowered and "enable javascript and cookies" in lowered)
        or "잠시만 기다리십시오" in html
        or "challenges.cloudflare.com" in lowered
    ):
        raise RuntimeError(
            "LUSH UK returned a Cloudflare challenge page. "
            "Run with browser-backed crawling or provide valid request headers/cookies."
        )


def normalize_product_url(raw_url: str) -> str:
    """Normalize relative or fragmented Lush UK product URLs."""
    absolute_url = urljoin(BASE_URL, raw_url)
    url_without_fragment = urldefrag(absolute_url).url
    parts = urlsplit(url_without_fragment)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def extract_image_url(link: Any) -> str:
    """Extract product image URL near a Lush UK product link."""
    card = link.find_parent(["article", "li"]) or link
    image = card.select_one("img") if hasattr(card, "select_one") else None
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


def normalize_image_url(raw_url: str) -> str:
    """Normalize Lush UK image URLs."""
    if raw_url.startswith("//"):
        raw_url = f"https:{raw_url}"
    return urljoin(BASE_URL, raw_url)


def build_product_url(english_name: str, product_type: str) -> str:
    """Build a likely Lush UK product URL from name and product type."""
    slug = slugify_product_name(english_name)
    if product_type == "Body Spray":
        slug = f"{slug}-body-spray"
    elif product_type == "Solid Perfume":
        slug = f"{slug}-solidperfume"
    elif product_type == "Perfume" and english_name != "29 High Street":
        slug = f"{slug}-perfume"
    return f"{BASE_URL}/uk/en/p/{slug}"


def infer_referenced_product_type(attribute_slug: str) -> str:
    """Infer product type from the known referenced attribute slug prefix."""
    prefix = attribute_slug.split("_", 1)[0]
    return {
        "123": "Perfume",
        "1126": "Body Spray",
        "124": "Solid Perfume",
    }.get(prefix, "")


def slugify_product_name(name: str) -> str:
    """Convert a product name into the Lush UK URL slug style."""
    slug = normalize_text(name).lower()
    slug = slug.replace(":", "")
    slug = re.sub(r"['’]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def product_card_text(link: Any) -> str:
    """Return normalized text for the product card containing a link."""
    card = link.find_parent(["article", "li"]) or link
    return normalize_text(" ".join(card.stripped_strings))


def infer_product_type(card_text: str, product_url: str) -> str:
    """Infer product type from card text or URL slug."""
    for product_type in PRODUCT_TYPES:
        if product_type in card_text:
            return product_type

    slug = product_url.rstrip("/").split("/")[-1]
    for product_type in PRODUCT_TYPES:
        if product_type.lower().replace(" ", "") in slug.replace("-", ""):
            return product_type
    return ""


def infer_product_name(card_text: str, product_type: str, product_url: str) -> str:
    """Infer product display name from card text or URL slug."""
    if card_text and product_type and product_type in card_text:
        name = normalize_text(card_text.split(product_type, 1)[0])
        if name:
            return name

    slug = product_url.rstrip("/").split("/")[-1]
    for suffix in ("-solidperfume", "-body-spray", "-perfume", "-wash-card", "-candle"):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
            break
    return normalize_text(slug.replace("-", " ").title())

# End of file.
