# Architecture

이 문서는 향수 데이터 크롤링 프로젝트의 현재 구조와 주요 설계 결정을 정리합니다.

## Goals

- 브랜드와 소스가 달라도 최종 JSON 구조를 동일하게 유지합니다.
- 크롤러는 원천 데이터를 최대한 보존하고, 공통 스키마 변환은 마지막 단계에서 수행합니다.
- 가격, 향조, 키워드는 원천 사이트에서 확인 가능한 값 위주로 저장합니다.
- 번역은 선택 기능으로 두고, API 키가 없을 때도 파이프라인이 실패하지 않게 합니다.

## Pipeline Layers

### Source Crawlers

`backend/pipelines/*_scraper.py`와 하위 패키지는 사이트별 데이터를 수집합니다. 이 계층은 HTML, JSON-LD, Next.js 데이터, 외부 export 파일처럼 각 사이트가 제공하는 구조를 읽습니다.

### Source Transformers

`backend/pipelines/fraganty/transform.py`, `backend/pipelines/fragrantica/transform.py`, `backend/pipelines/persona_sources.py`, `backend/pipelines/retail_multibrand_scraper.py`는 원천별 필드를 프로젝트 내부 row로 맞춥니다.

### Normalized Schema

`backend/pipelines/common/normalized_schema.py`가 최종 계약을 책임집니다. 이 파일은 이름, 가격, 제품 subtype, 설명, 노트, 향조, 키워드, 메타데이터를 동일한 형태로 정리합니다.

### Data Outputs

`data/*.json`은 최종 산출물입니다. 파일명은 보통 `{brand}_{source}_fragrance_data.json` 또는 `{brand}_korea_fragrance_data.json` 형태를 사용합니다.

## Important Decisions

### Source-backed Taxonomy

`accords`와 `keywords`는 노트 기반 추론으로 자동 생성하지 않습니다. 이전에는 누락을 줄이기 위해 추론값을 채웠지만, 데이터 신뢰도를 위해 원천 사이트가 제공한 값만 저장하는 방식으로 변경했습니다.

### Missing Price Policy

가격을 원천에서 확인할 수 있으면 반드시 `price.raw`, `price.amount`, `price.currency`에 저장합니다. 원천이 가격을 제공하지 않는 Fragrantica 계열 데이터는 `meta.price_missing_reason = "source_unavailable"`로 표시합니다.

### Optional DeepL Translation

영어 이름만 있는 데이터는 `DEEPL_API_KEY`가 있을 때만 한국어 이름 번역을 시도합니다. 키가 없으면 `NullTranslator`가 빈 값을 반환하므로 로컬 테스트와 CI가 외부 API에 의존하지 않습니다.

