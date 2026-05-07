"""Utilities for retail crawler exports that already match the local product schema."""

from __future__ import annotations

import json
from typing import Any


CURRENCY_SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£", "KRW": "₩"}
ALLOWED_FRAGRANCE_TYPES = {"Eau de Parfum", "Eau de Toilette", "Parfum", "Body Spray", "Hair Mist", "Solid Perfume"}
NON_FRAGRANCE_TITLE_KEYWORDS = [
    "candle",
    "body oil",
    "body lotion",
    "body cream",
    "eye",
    "lip",
    "powder",
    "primer",
    "foundation",
    "mascara",
    "gift set",
]


def load_mysql_ready_products(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract product rows from a MySQL-ready crawler export."""
    products = payload.get("products", [])
    if not isinstance(products, list):
        return []
    return [product for product in products if isinstance(product, dict)]


def load_jsonl_products(raw_text: str) -> list[dict[str, Any]]:
    """Read product rows from newline-delimited JSON text."""
    products: list[dict[str, Any]] = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            products.append(payload)
    return products


def format_price(amount: float | int | None, currency: str) -> str:
    """Format retail crawler numeric prices with a currency symbol."""
    if amount is None:
        return ""
    if currency == "KRW":
        return f"{int(amount):,}원"
    symbol = CURRENCY_SYMBOL.get(currency, f"{currency} ")
    return f"{symbol}{float(amount):,.2f}"


def is_probably_fragrance_product(name: str, product_type: str, url: str = "") -> bool:
    """Filter obvious non-fragrance products from retail crawler candidates."""
    title = (name or "").lower()
    if not title or "404 not found" in title or "not found" in title:
        return False
    if any(keyword in title for keyword in NON_FRAGRANCE_TITLE_KEYWORDS):
        return "body spray" in title or "hair mist" in title
    if product_type in ALLOWED_FRAGRANCE_TYPES:
        return True
    return any(
        token in f"{title} {url.lower()}"
        for token in ["eau de parfum", "eau de toilette", "parfum", "body spray", "hair mist", "solid perfume"]
    )

# End of file.
