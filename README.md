# 08 Data Playground

향수 브랜드별 공식몰, Fragrantica, Fraganty, Persona-L 크롤러 산출물을 하나의 JSON 데이터 계약으로 정규화하는 데이터 수집 프로젝트입니다.

현재 저장소의 핵심 목표는 서로 다른 사이트에서 가져온 향수 데이터를 `data/*.json` 형태로 일관되게 관리하는 것입니다. 크롤러별 원천 필드는 다르지만 최종 산출물은 `source`, `brand`, `price`, `notes`, `accords`, `keywords`, `meta` 같은 공통 필드를 갖습니다.

## Overview

이 프로젝트는 다음 흐름으로 동작합니다.

1. 브랜드별 크롤러가 원천 데이터를 수집합니다.
2. `backend/pipelines/common/normalized_schema.py`가 공통 스키마로 변환합니다.
3. 영어 이름만 있는 데이터는 `.env`의 DeepL API 설정이 있을 때 한국어 이름을 보강합니다.
4. 최종 JSON은 `data/` 아래에 브랜드/소스별 파일로 저장합니다.

`accords`와 `keywords`는 임의 추론으로 채우지 않습니다. 사이트나 원천 데이터가 직접 제공한 값만 반영하는 것을 기본 정책으로 둡니다.

## Tech Stack

- Backend: Python
- Crawling/Parsing: `requests`, `BeautifulSoup`, Selenium 계열 유틸리티
- Translation: DeepL API
- Testing: `pytest`
- Documentation: Markdown, mdBook wiki

## Structure

```text
.
├── .github/
│   └── workflows/
├── backend/
│   ├── pipelines/
│   │   ├── common/
│   │   ├── fraganty/
│   │   ├── fragrantica/
│   │   ├── lush_korea/
│   │   ├── lush_uk/
│   │   └── ...
│   └── tests/
├── data/
│   └── *_fragrance_data.json
├── docs/
├── wiki/
│   ├── book.toml
│   └── src/
│       ├── SUMMARY.md
│       ├── overview.md
│       ├── conventions.md
│       └── conventions/
│           ├── git-flow.md
│           ├── commit.md
│           ├── naming.md
│           └── code-style.md
├── README.md
└── LICENSE
```

## Directory Guide

- `backend/pipelines/`: 브랜드/소스별 크롤러와 변환 로직
- `backend/pipelines/common/`: 공통 HTTP, 브라우저, 텍스트, 출력, 번역, 정규화 유틸리티
- `backend/tests/`: 크롤러 파서와 정규화 계약 테스트
- `data/`: 정규화된 향수 JSON 산출물
- `docs/`: 설계 문서와 데이터 계약 문서
- `wiki/`: 팀 내부 지식 기반과 운영 규칙
- `.github/`: GitHub template, workflow, automation 설정

## Data Contract

최종 JSON row는 아래 구조를 기준으로 합니다.

```json
{
  "source": "official | fragrantica | fraganty | retail",
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

자세한 필드 정책은 [docs/data-contract.md](./docs/data-contract.md)를 참고합니다.

## Environment Variables

`.env.example`을 참고해 `.env`를 구성합니다.

```bash
DEEPL_API_KEY=
DEEPL_API_URL=https://api-free.deepl.com/v2/translate
```

`DEEPL_API_KEY`가 없으면 번역은 수행하지 않고 빈 한국어 이름은 그대로 둡니다. 실제 API 키는 `.env`에만 넣고 커밋하지 않습니다.

## Commands

테스트는 아래 명령으로 실행합니다.

```bash
python -m pytest backend\tests
```

개별 크롤러는 모듈 단위로 실행합니다.

```bash
$env:PYTHONPATH='backend'; python -m pipelines.lush_korea_scraper
```

Windows PowerShell 기준 예시입니다. 다른 셸에서는 `PYTHONPATH=backend` 설정 문법만 바꾸면 됩니다.

## Crawler Sources

- Official: Chanel Korea, Lush Korea, Lush UK, Jo Malone Korea, Granhand, Creed, Byredo, Le Labo, Nag Champa 등
- Fraganty: Bvlgari, Chanel, Dior 향수 데이터
- Fragrantica: Giorgio Armani, Maison Francis Kurkdjian 향수 데이터
- Retail exports: Tom Ford, Diptyque 계열 변환 유틸리티

각 소스의 원천 필드는 다르기 때문에, 크롤러는 가능한 한 원천 데이터를 보존하고 마지막 단계에서만 공통 스키마로 변환합니다.

## Testing

테스트는 크게 세 범위를 검증합니다.

- HTML/JSON 파서가 사이트 구조에서 필요한 필드를 읽는지
- `normalize_product_row`가 공통 데이터 계약을 지키는지
- 외부 소스 변환기가 가격, 노트, 향조, 키워드 정책을 유지하는지

최근 전체 검증 기준:

```bash
python -m pytest backend\tests
```

## Wiki

프로젝트 규칙은 `wiki/` 아래 mdBook 문서로 관리합니다.

주요 문서:

- [Overview](./wiki/src/overview.md)
- [Data Contract](./wiki/src/data-contract.md)
- [Crawler Pipelines](./wiki/src/crawler-pipelines.md)
- [Environment](./wiki/src/environment.md)
- [Conventions](./wiki/src/conventions.md)

## Documentation

설계와 데이터 계약은 `docs/`에도 별도 문서로 남깁니다.

- [Architecture](./docs/architecture.md)
- [Data Contract](./docs/data-contract.md)
- [Crawler Operations](./docs/crawler-operations.md)

## GitHub Actions

이 저장소는 GitHub Actions workflow를 통해 다음 작업을 수행할 수 있도록 구성합니다.

- mdBook 기반 wiki 배포
- PR 코드 리뷰 자동화

프로젝트에 맞게 브랜치 이름, secrets, action 버전을 확인한 뒤 사용합니다.

## License

See [LICENSE](./LICENSE).
