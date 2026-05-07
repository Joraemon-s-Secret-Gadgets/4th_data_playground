# Environment

프로젝트 실행에 필요한 환경 변수와 명령을 정리합니다.

## DeepL

영어 이름을 한국어 이름으로 보강하려면 `.env`에 DeepL API 키를 넣습니다.

```bash
DEEPL_API_KEY=your-key
DEEPL_API_URL=https://api-free.deepl.com/v2/translate
```

`DEEPL_API_KEY`가 없으면 번역은 건너뜁니다. 이 동작은 로컬 테스트와 CI가 외부 API에 의존하지 않게 하기 위한 의도된 정책입니다.

## Python Path

크롤러 모듈은 `backend`를 import root로 사용합니다.

PowerShell:

```powershell
$env:PYTHONPATH='backend'
python -m pipelines.lush_korea_scraper
```

## Testing

전체 테스트:

```bash
python -m pytest backend\tests
```

정규화 계약 테스트:

```bash
python -m pytest backend\tests\test_normalized_schema.py
```

## Secrets

`.env`는 커밋하지 않습니다. 공유가 필요한 값은 `.env.example`에 key 이름과 기본 URL만 기록합니다.
