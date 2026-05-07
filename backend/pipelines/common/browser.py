"""Browser-backed fetching utilities for dynamic pages."""

from __future__ import annotations

import os
import tempfile
import time
from typing import Any


DriverFactory = Any


def fetch_rendered_html(
    url: str,
    *,
    driver_factory: DriverFactory | None = None,
    wait_seconds: float = 5,
) -> str:
    """Return rendered page HTML using a Selenium-compatible driver."""
    driver = (driver_factory or _create_default_webdriver)()
    try:
        driver.get(url)
        time.sleep(wait_seconds)
        return str(driver.page_source)
    finally:
        driver.quit()


def _create_default_webdriver() -> Any:
    """Create the default headless Chrome webdriver."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    cache_path = os.getenv("SELENIUM_MANAGER_CACHE") or os.path.join(os.getcwd(), ".selenium-cache")
    os.environ.setdefault("SE_CACHE_PATH", cache_path)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1440,1200")
    options.add_argument(f"--user-data-dir={tempfile.mkdtemp(prefix='selenium-chrome-')}")
    return webdriver.Chrome(options=options)

# End of file.
