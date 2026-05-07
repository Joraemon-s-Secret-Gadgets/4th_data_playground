"""Category parsing helpers for Fraganty brand pages."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup


BASE_URL = "https://fraganty.ai"


def extract_perfume_links(html: str, *, base_url: str = BASE_URL) -> list[str]:
    """Extract unique perfume detail links from a Fraganty brand page."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()

    for node in soup.select("a.group.block[href], a[href*='/perfume/']"):
        href = str(node.get("href") or "")
        if not href or "goto" in href:
            continue

        url = normalize_fraganty_url(href, base_url=base_url)
        if "/perfume/" not in url or url in seen:
            continue

        links.append(url)
        seen.add(url)

    return links


def normalize_fraganty_url(href: str, *, base_url: str = BASE_URL) -> str:
    """Normalize a Fraganty link by removing query strings and trailing slashes."""
    url = urljoin(base_url, href)
    split_url = urlsplit(url)
    return urlunsplit((split_url.scheme, split_url.netloc, split_url.path.rstrip("/"), "", ""))


def perfume_name_from_url(url: str) -> str:
    """Build a readable lowercase perfume name from a Fraganty product URL."""
    path = urlsplit(url).path.rstrip("/")
    slug = path.rsplit("/", 1)[-1]
    return slug.replace("-", " ").strip().lower() or "unknown"

# End of file.
