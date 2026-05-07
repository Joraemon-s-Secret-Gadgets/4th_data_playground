"""Translation clients used by scraper normalization."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol

import requests


class Translator(Protocol):
    """Minimal translator interface for schema normalization."""

    def translate(self, text: str, *, target_lang: str = "KO", source_lang: str = "EN") -> str:
        """Translate one text value."""


class NullTranslator:
    """Translator that leaves missing translated values empty when no API key is configured."""

    def translate(self, text: str, *, target_lang: str = "KO", source_lang: str = "EN") -> str:
        return ""


class DeepLTranslator:
    """Small DeepL API client configured through environment variables."""

    def __init__(
        self,
        *,
        api_key: str,
        api_url: str = "https://api-free.deepl.com/v2/translate",
        session: Any | None = None,
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key
        self.api_url = api_url
        self.session = session or requests.Session()
        self.timeout = timeout
        self._cache: dict[tuple[str, str, str], str] = {}

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "DeepLTranslator | NullTranslator":
        """Create a DeepL translator from environment variables or a project .env file."""
        dotenv = _read_dotenv(env_path)
        api_key = (os.getenv("DEEPL_API_KEY") or dotenv.get("DEEPL_API_KEY", "")).strip()
        if not api_key:
            return NullTranslator()
        api_url = (os.getenv("DEEPL_API_URL") or dotenv.get("DEEPL_API_URL", "https://api-free.deepl.com/v2/translate")).strip()
        return cls(api_key=api_key, api_url=api_url)

    def translate(self, text: str, *, target_lang: str = "KO", source_lang: str = "EN") -> str:
        """Translate text through DeepL, caching identical requests in-process."""
        value = str(text or "").strip()
        if not value:
            return ""

        cache_key = (value, source_lang, target_lang)
        if cache_key in self._cache:
            return self._cache[cache_key]

        response = self.session.post(
            self.api_url,
            headers={
                "Authorization": f"DeepL-Auth-Key {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"text": [value], "source_lang": source_lang, "target_lang": target_lang},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        translated = str((payload.get("translations") or [{}])[0].get("text") or "").strip()
        self._cache[cache_key] = translated or value
        return self._cache[cache_key]


def _read_dotenv(env_path: str | Path) -> dict[str, str]:
    """Read simple KEY=VALUE entries from a dotenv file without exposing secrets."""
    path = Path(env_path)
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values

# End of file.
