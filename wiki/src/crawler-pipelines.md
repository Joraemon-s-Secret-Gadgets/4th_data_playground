# Crawler Pipelines

이 문서는 크롤러와 변환 계층의 역할을 설명합니다.

## Common Flow

1. 사이트별 크롤러가 HTML, JSON-LD, Next.js 데이터, 외부 export를 읽습니다.
2. 소스별 transform 함수가 원천 필드를 내부 row로 맞춥니다.
3. `normalize_product_row` 또는 `normalize_product_rows`가 공통 데이터 계약으로 변환합니다.
4. 최종 결과를 `data/*.json`에 저장합니다.

## Core Modules

- `backend/pipelines/common/normalized_schema.py`: 최종 데이터 계약 변환
- `backend/pipelines/common/translation.py`: DeepL 번역 클라이언트
- `backend/pipelines/fraganty/transform.py`: Fraganty enriched export 변환
- `backend/pipelines/fragrantica/transform.py`: Fragrantica CSV/JSON export 변환
- `backend/pipelines/persona_sources.py`: Persona-L export 변환
- `backend/pipelines/retail_multibrand_scraper.py`: retail crawler 문서 변환

## Taxonomy Policy

`accords`와 `keywords`는 데이터 품질에 직접 영향을 줍니다. 따라서 사이트가 제공하지 않는 값을 자동으로 추론해서 저장하지 않습니다.

예외적으로, 원천 export에 `family`, `main_accords`, AI 분석 키워드처럼 명시 필드가 있으면 해당 값을 사용합니다.

## Adding a New Crawler

새 크롤러를 추가할 때는 아래 순서를 따릅니다.

1. 원천 사이트에서 읽을 수 있는 필드를 테스트 fixture로 먼저 정리합니다.
2. 파서 함수가 원천 필드를 안정적으로 반환하도록 테스트를 작성합니다.
3. 최종 저장 직전에 `normalize_product_rows`를 호출합니다.
4. `data/` 산출물이 공통 계약을 지키는지 테스트합니다.
5. README 또는 wiki의 source 목록을 갱신합니다.

