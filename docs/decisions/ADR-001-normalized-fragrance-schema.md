# ADR-001: Normalize Fragrance Data With a Shared Contract

## Status

Accepted

## Date

2026-05-07

## Context

브랜드별 크롤러가 서로 다른 형태의 row를 만들고 있었습니다. 공식몰, Fraganty, Fragrantica, Persona-L export는 가격, 이름, 노트, 향조, 키워드 필드 이름과 표현 방식이 모두 달랐습니다.

데이터를 후속 분석이나 서비스에서 쓰려면 소스별 예외 처리를 줄이고, 최종 JSON의 필드 계약을 명확히 해야 했습니다.

## Decision

`backend/pipelines/common/normalized_schema.py`를 공통 변환 계층으로 두고, 모든 크롤러 산출물이 최종적으로 같은 JSON 계약을 따르도록 했습니다.

또한 `accords`와 `keywords`는 추론값이 아니라 원천 사이트 또는 원천 export가 제공한 값만 저장하는 정책을 채택했습니다. 가격이 제공되지 않는 소스는 빈 가격과 함께 `meta.price_missing_reason`을 기록합니다.

## Alternatives Considered

### Keep Source-specific JSON Shapes

- 장점: 크롤러 구현이 간단합니다.
- 단점: 후속 처리에서 소스별 분기와 예외가 계속 늘어납니다.
- 결론: 데이터 소비자가 안정적인 계약을 기대하기 어렵기 때문에 거절했습니다.

### Infer Missing Accords and Keywords

- 장점: 빈 필드를 줄일 수 있습니다.
- 단점: 원천에 없는 정보가 실제 크롤링 데이터처럼 보일 수 있습니다.
- 결론: 데이터 신뢰도를 위해 추론값 저장을 기본 정책에서 제외했습니다.

## Consequences

- 새 크롤러는 공통 스키마 변환을 반드시 거쳐야 합니다.
- 원천 가격이 없는 데이터는 명시적으로 누락 사유를 남깁니다.
- `accords`와 `keywords`의 빈 값은 오류가 아니라 원천 미제공을 의미할 수 있습니다.
- 테스트는 데이터 계약과 소스별 변환 정책을 함께 검증해야 합니다.
