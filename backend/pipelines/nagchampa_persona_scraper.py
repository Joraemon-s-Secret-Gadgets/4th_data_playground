"""Persona-L Nag Champa export를 다루는 얇은 facade 모듈입니다.

Nag Champa의 가격은 공식 사이트에서 확인 가능한 판매가를 데이터에 반영했고,
상품명 기반 생성 키워드는 원천 키워드가 아니므로 최종 schema에서는 비웁니다.
"""

from pipelines.persona_sources import format_persona_rows


BRAND = "Nag Champa"
DEFAULT_OUTPUT_PATH = "data/nagchampa_korea_fragrance_data.json"

__all__ = ["BRAND", "DEFAULT_OUTPUT_PATH", "format_persona_rows"]

# End of file.
