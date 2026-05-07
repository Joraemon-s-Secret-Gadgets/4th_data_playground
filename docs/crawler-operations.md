# Crawler Operations

이 문서는 크롤러 실행과 유지보수 기준을 정리합니다.

## Setup

Python 의존성은 `backend/requirements.txt`와 `backend/requirements-dev.txt`를 기준으로 설치합니다.

```bash
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

DeepL 번역이 필요하면 `.env`에 아래 값을 넣습니다.

```bash
DEEPL_API_KEY=your-key
DEEPL_API_URL=https://api-free.deepl.com/v2/translate
```

## Run

PowerShell 기준 실행 예시는 다음과 같습니다.

```powershell
$env:PYTHONPATH='backend'
python -m pipelines.lush_korea_scraper
```

Selenium이나 동적 렌더링이 필요한 크롤러는 환경 변수로 fetcher를 바꿀 수 있습니다.

```powershell
$env:PYTHONPATH='backend'
$env:CHANEL_KR_USE_SELENIUM='true'
python -m pipelines.chanel_korea_scraper
```

## Test

전체 테스트:

```bash
python -m pytest backend\tests
```

정규화 계약만 확인:

```bash
python -m pytest backend\tests\test_normalized_schema.py
```

## Maintenance Rules

- 새 크롤러는 원천 필드를 먼저 안정적으로 수집하고, 마지막에 `normalize_product_row` 또는 `normalize_product_rows`를 호출합니다.
- 가격 파싱 로직을 각 크롤러에 흩뿌리지 말고 가능한 `parse_price`가 처리할 수 있는 표시 문자열을 넘깁니다.
- `accords`와 `keywords`는 원천 사이트가 제공하지 않으면 비워둡니다.
- 사이트 구조가 바뀌면 테스트 fixture를 먼저 업데이트하고 파서를 수정합니다.

