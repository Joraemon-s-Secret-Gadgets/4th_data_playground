"""HTTP helpers shared by scraper pipelines."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests


def build_request_headers(env_prefix: str) -> dict[str, str]:
    """Build request headers from environment variables with a shared prefix."""
    headers: dict[str, str] = {}
    raw_headers = os.getenv(f"{env_prefix}_REQUEST_HEADERS")

    if raw_headers:
        parsed = json.loads(raw_headers)
        if not isinstance(parsed, dict):
            raise ValueError(f"{env_prefix}_REQUEST_HEADERS must be a JSON object.")
        headers.update({str(key): str(value) for key, value in parsed.items()})

    if user_agent := os.getenv(f"{env_prefix}_USER_AGENT"):
        headers["User-Agent"] = user_agent

    if accept_language := os.getenv(f"{env_prefix}_ACCEPT_LANGUAGE"):
        headers["Accept-Language"] = accept_language

    return headers


def get_with_retries(
    session_or_url: requests.Session | str,
    url: str | None = None,
    *,
    retries: int = 3,
    backoff_seconds: float = 0.5,
    **kwargs: Any,
) -> requests.Response:
    """Run a GET request with simple retry and linear backoff."""
    if isinstance(session_or_url, requests.Session):
        session = session_or_url
        request_url = url
    else:
        session = requests
        request_url = session_or_url

    if request_url is None:
        raise ValueError("request URL is required.")

    last_error: requests.RequestException | None = None
    for attempt in range(retries):
        try:
            return session.get(request_url, **kwargs)
        except requests.RequestException as error:
            last_error = error
            if attempt == retries - 1:
                break
            time.sleep(backoff_seconds * (attempt + 1))

    if last_error is None:
        raise RuntimeError("request failed without an exception.")
    raise last_error

# End of file.
