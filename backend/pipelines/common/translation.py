"""정규화 과정에서 사용하는 번역 클라이언트입니다.

DeepL API 키가 있으면 실제 번역을 수행하고, 키가 없으면 `NullTranslator`로
조용히 건너뜁니다. 이 구조 덕분에 테스트와 CI는 외부 API 없이도 실행됩니다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol

import requests


class Translator(Protocol):
    """정규화 계층이 기대하는 최소 번역기 인터페이스입니다."""

    def translate(self, text: str, *, target_lang: str = "KO", source_lang: str = "EN") -> str:
        """문자열 하나를 지정 언어로 번역합니다."""


class NullTranslator:
    """API 키가 없을 때 번역을 수행하지 않는 안전한 대체 번역기입니다."""

    def translate(self, text: str, *, target_lang: str = "KO", source_lang: str = "EN") -> str:
        return ""


class DeepLTranslator:
    """환경 변수 또는 `.env`로 설정되는 작은 DeepL API 클라이언트입니다."""

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
        """환경 변수와 `.env` 파일에서 DeepL 설정을 읽어 번역기를 생성합니다."""
        dotenv = _read_dotenv(env_path)
        api_key = (os.getenv("DEEPL_API_KEY") or dotenv.get("DEEPL_API_KEY", "")).strip()
        if not api_key:
            return NullTranslator()
        api_url = (os.getenv("DEEPL_API_URL") or dotenv.get("DEEPL_API_URL", "https://api-free.deepl.com/v2/translate")).strip()
        return cls(api_key=api_key, api_url=api_url)

    def translate(self, text: str, *, target_lang: str = "KO", source_lang: str = "EN") -> str:
        """DeepL로 텍스트를 번역하고, 같은 요청은 프로세스 내부 캐시에서 재사용합니다."""
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
    """비밀값을 출력하지 않고 단순한 `KEY=VALUE` 형식의 dotenv 파일을 읽습니다."""
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
