# Data Contract

최종 산출물은 `data/*.json` 파일입니다. 모든 row는 공통 필드를 갖습니다.

## Required Shape

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
  "product_url": "https://...",
  "image_url": "https://...",
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

## Rules

- `brand`는 대문자로 저장합니다.
- `product_type`은 현재 `perfume`으로 통일합니다.
- `product_subtype`은 원천 상품 타입을 안정적인 snake_case 값으로 변환합니다.
- `price.raw`는 사이트 표시 문자열, `price.amount`는 숫자, `price.currency`는 통화 코드입니다.
- 원천 가격이 없으면 `meta.price_missing_reason = "source_unavailable"`를 기록합니다.
- `accords`와 `keywords`는 원천 사이트나 원천 export에서 제공한 값만 저장합니다.
- 노트 기반 향조/키워드 추론값은 최종 데이터에 넣지 않습니다.

## Source-specific Notes

- Fraganty는 AI 분석 키워드와 main accords를 제공하므로 `keywords`와 `accords`가 채워질 수 있습니다.
- Fragrantica는 accords와 notes를 제공하지만 판매 가격은 제공하지 않습니다.
- Byredo/Le Labo Persona-L 데이터는 `personalData.ts`의 `price`와 `family`를 원천으로 사용합니다.
- Nag Champa 가격은 공식 사이트의 15g 상품 판매가를 기준으로 보강했습니다.

