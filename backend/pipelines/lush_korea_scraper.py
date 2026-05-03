from __future__ import annotations

import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests


DEFAULT_URL = "https://www.lush.co.kr/"
PERFUME_KEYWORDS = (
    "향수",
    "퍼퓸",
    "프래그런스",
    "perfume",
    "fragrance",
    "body spray",
    "보디 스프레이",
    "바디 스프레이",
)


class LushHomepageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.candidates: list[str] = []
        self._capture_anchor = False
        self._anchor_parts: list[str] = []
        self._json_ld_parts: list[str] = []
        self._in_json_ld = False
        self.text_nodes: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}

        if tag == "a":
            href = attr_map.get("href", "")
            self._capture_anchor = _is_perfume_related(href)
            self._anchor_parts = []

        if tag == "img":
            alt = attr_map.get("alt", "").strip()
            if _is_perfume_related(alt):
                self.candidates.append(alt)

        if tag == "script" and attr_map.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        text = _normalize_text(data)
        if text:
            self.text_nodes.append(text)

        if self._capture_anchor:
            self._anchor_parts.append(data)

        if self._in_json_ld:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_anchor:
            label = _normalize_text(" ".join(self._anchor_parts))
            if label:
                self.candidates.append(label)
            self._capture_anchor = False
            self._anchor_parts = []

        if tag == "script" and self._in_json_ld:
            self.candidates.extend(_extract_json_ld_product_names("".join(self._json_ld_parts)))
            self._in_json_ld = False
            self._json_ld_parts = []


def build_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    raw_headers = os.getenv("LUSH_KR_REQUEST_HEADERS")

    if raw_headers:
        parsed = json.loads(raw_headers)
        if not isinstance(parsed, dict):
            raise ValueError("LUSH_KR_REQUEST_HEADERS must be a JSON object.")
        headers.update({str(key): str(value) for key, value in parsed.items()})

    if user_agent := os.getenv("LUSH_KR_USER_AGENT"):
        headers["User-Agent"] = user_agent

    if accept_language := os.getenv("LUSH_KR_ACCEPT_LANGUAGE"):
        headers["Accept-Language"] = accept_language

    return headers


def extract_perfume_names(html: str) -> list[str]:
    parser = LushHomepageParser()
    parser.feed(html)

    names: list[str] = []
    seen: set[str] = set()
    candidates = [*parser.candidates, *_extract_fragrance_section_names(parser.text_nodes)]
    for candidate in candidates:
        name = _normalize_text(candidate)
        if name and name not in seen:
            names.append(name)
            seen.add(name)
    return names


def fetch_homepage(url: str = DEFAULT_URL) -> str:
    response = requests.get(url, headers=build_headers(), timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def scrape_perfume_names(url: str = DEFAULT_URL) -> list[dict[str, str]]:
    html = fetch_homepage(url)
    return [{"country": "KR", "name": name} for name in extract_perfume_names(html)]


def main() -> None:
    url = os.getenv("LUSH_KR_HOME_URL", DEFAULT_URL)
    output_path = Path(os.getenv("LUSH_KR_OUTPUT_PATH", "data/lush_korea_perfume_names.json"))
    rows = scrape_perfume_names(url)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def _extract_json_ld_product_names(raw_json: str) -> list[str]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return []

    names: list[str] = []
    for node in _walk_json(payload):
        if isinstance(node, dict) and node.get("@type") == "Product":
            name = node.get("name")
            if isinstance(name, str) and _is_perfume_related(name):
                names.append(name)
    return names


def _walk_json(value: Any) -> list[Any]:
    nodes = [value]
    if isinstance(value, dict):
        for child in value.values():
            nodes.extend(_walk_json(child))
    elif isinstance(value, list):
        for child in value:
            nodes.extend(_walk_json(child))
    return nodes


def _is_perfume_related(value: str) -> bool:
    lowered = value.lower()
    return any(keyword in lowered for keyword in PERFUME_KEYWORDS)


def _extract_fragrance_section_names(text_nodes: list[str]) -> list[str]:
    product_types = {"보디 스프레이", "바디 스프레이", "퍼퓸", "솔리드 퍼퓸", "워시 카드", "캔들"}
    stop_sections = {"기프트", "매장 찾기"}

    try:
        start = text_nodes.index("프래그런스")
    except ValueError:
        return []

    names: list[str] = []
    for index in range(start + 1, len(text_nodes)):
        current = text_nodes[index]
        if current in stop_sections:
            break
        if current in product_types and index > 0:
            candidate = text_nodes[index - 1]
            if candidate not in product_types and candidate not in stop_sections:
                names.append(candidate)
    return names


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


if __name__ == "__main__":
    main()
