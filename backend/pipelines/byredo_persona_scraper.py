"""Persona-L Byredo export를 다루는 얇은 facade 모듈입니다.

브랜드별 실행 진입점에서 공통 `format_persona_rows`를 재사용하기 위해
브랜드명과 기본 출력 경로만 이 파일에 둡니다.
"""

from pipelines.persona_sources import format_persona_rows


BRAND = "Byredo"
DEFAULT_OUTPUT_PATH = "data/byredo_korea_fragrance_data.json"

__all__ = ["BRAND", "DEFAULT_OUTPUT_PATH", "format_persona_rows"]

# End of file.
