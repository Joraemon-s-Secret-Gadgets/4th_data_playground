# Data Contract

이 문서는 `data/*.json` 파일의 row 구조를 설명합니다.

## Row Shape

```json
{
  "source": "official",
  "source_country": "KR",
  "brand": "CHANEL",
  "korean_name": "코코 마드모아젤",
  "english_name": "coco mademoiselle",
  "normalized_name": "coco mademoiselle",
  "product_type": "perfume",
  "product_subtype": "eau_de_parfum",
  "product_url": "https://example.test/product",
  "image_url": "https://example.test/image.jpg",
  "price": {
    "raw": "152,000 원",
    "amount": 152000,
    "currency": "KRW"
  },
  "description": "",
  "ingredients_raw": "",
  "notes": ["오렌지", "자스민", "패출리"],
  "accords": ["citrus", "woody"],
  "keywords": {
    "ko": ["우아한"],
    "en": ["Elegant"]
  },
  "meta": {
    "release_year": null,
    "original_product_type": "오 드 빠르펭",
    "original_country": "KR"
  }
}
```

## Field Policy

- `source`: `official`, `fragrantica`, `fraganty`, `retail` 중 하나를 기본으로 사용합니다.
- `source_country`: 수집 사이트 또는 브랜드 출처 국가입니다.
- `brand`: 대문자 브랜드명으로 저장합니다.
- `korean_name`: 한국어 상품명입니다. DeepL 번역이 켜져 있을 때 보강될 수 있습니다.
- `english_name`: 영어 상품명입니다.
- `normalized_name`: 매칭용 이름입니다. 영문/숫자 중심으로 소문자 정규화합니다.
- `product_type`: 현재 최종 계약에서는 `perfume`으로 고정합니다.
- `product_subtype`: 원천 제품 타입을 `eau_de_parfum`, `eau_de_toilette`, `incense_stick` 같은 안정적인 값으로 변환합니다.
- `price.raw`: 사이트에서 보이는 가격 문자열입니다.
- `price.amount`: 숫자 가격입니다.
- `price.currency`: `KRW`, `USD`, `EUR`, `GBP` 등 통화 코드입니다.
- `description`: 원천 설명이 있으면 원천 설명을 우선합니다. 없으면 노트/향조 기반의 짧은 설명을 만들 수 있습니다.
- `notes`: 탑/하트/베이스 또는 key ingredient를 평탄화한 배열입니다.
- `accords`: 원천 사이트가 제공한 향조나 family 값입니다. 노트 기반 추론값은 넣지 않습니다.
- `keywords`: 원천 데이터가 제공한 키워드입니다. AI 분석 결과가 원천 export에 포함된 Fraganty 계열은 유지합니다.
- `meta.price_missing_reason`: 원천이 가격을 제공하지 않을 때 `source_unavailable`로 표시합니다.

## Source Notes

- Fraganty는 가격, 향조, AI 분석 키워드를 제공하므로 `accords`와 `keywords`가 채워집니다.
- Fragrantica는 향조와 노트는 제공하지만 판매 가격은 제공하지 않아 가격 누락 사유를 기록합니다.
- 공식몰 계열은 가격과 설명을 우선 수집합니다. 향조/키워드는 사이트에 명시된 경우에만 저장합니다.
- Persona-L Byredo/Le Labo는 `personalData.ts`의 가격과 `family` 값을 원천으로 사용합니다.

