"""Tests for the normalized fragrance output schema."""

from pipelines.common.normalized_schema import normalize_product_row, normalize_product_rows, parse_price
from pipelines.common.translation import DeepLTranslator


def test_parse_price_extracts_krw_amount_and_currency() -> None:
    assert parse_price("152,000 원") == {"raw": "152,000 원", "amount": 152000, "currency": "KRW"}


def test_parse_price_extracts_symbol_currency() -> None:
    assert parse_price("€330.00") == {"raw": "€330.00", "amount": 330.0, "currency": "EUR"}


def test_normalize_product_row_maps_legacy_row_to_contract() -> None:
    row = normalize_product_row(
        {
            "country": "KR",
            "brand": "CHANEL",
            "korean_name": "코코 마드모아젤",
            "english_name": "coco mademoiselle",
            "product_type": "오 드 빠르펭",
            "product_url": "https://example.test/chanel",
            "regular_price": "152,000 원",
            "image_url": "https://example.test/chanel.jpg",
            "ingredients": "에탄올, 향료",
            "key_ingredients": ["오렌지", "자스민", "패출리"],
            "accords": ["citrus", "woody", "sweet"],
            "ko_keywords": ["상큼한", "차분한", "달콤한"],
        },
        source="official",
        source_country="KR",
        brand="CHANEL",
    )

    assert row == {
        "source": "official",
        "source_country": "KR",
        "brand": "CHANEL",
        "korean_name": "코코 마드모아젤",
        "english_name": "coco mademoiselle",
        "normalized_name": "coco mademoiselle",
        "product_type": "perfume",
        "product_subtype": "eau_de_parfum",
        "product_url": "https://example.test/chanel",
        "image_url": "https://example.test/chanel.jpg",
        "price": {"raw": "152,000 원", "amount": 152000, "currency": "KRW"},
        "description": "코코 마드모아젤은 오렌지, 자스민, 패출리 노트가 중심이며 citrus, woody, sweet 분위기를 가진 향수입니다.",
        "ingredients_raw": "에탄올, 향료",
        "notes": ["오렌지", "자스민", "패출리"],
        "accords": ["citrus", "woody", "sweet"],
        "keywords": {"ko": ["상큼한", "차분한", "달콤한"], "en": []},
        "meta": {
            "release_year": None,
            "original_product_type": "오 드 빠르펭",
            "original_country": "KR",
        },
    }


def test_normalize_product_rows_can_translate_missing_korean_names() -> None:
    class FakeTranslator:
        def translate(self, text: str, *, target_lang: str = "KO", source_lang: str = "EN") -> str:
            return {"Aventus": "아벤투스"}.get(text, text)

    rows = normalize_product_rows(
        [{"country": "UK", "english_name": "Aventus", "product_type": "Fragrance"}],
        source="official",
        source_country="UK",
        brand="CREED",
        translator=FakeTranslator(),
    )

    assert rows[0]["korean_name"] == "아벤투스"


def test_normalize_product_row_generates_description_from_notes() -> None:
    row = normalize_product_row(
        {
            "country": "IT",
            "brand": "BVLGARI",
            "korean_name": "옴니아 크리스탈린",
            "english_name": "omnia crystalline",
            "product_type": "향수",
            "key_ingredients": ["대나무", "연꽃", "머스크"],
            "accords": ["우디", "플로럴"],
        },
        source="fraganty",
        source_country="IT",
        brand="BVLGARI",
    )

    assert row["description"] == "옴니아 크리스탈린은 대나무, 연꽃, 머스크 노트가 중심이며 우디, 플로럴 분위기를 가진 향수입니다."


def test_normalize_product_row_can_skip_description_generation() -> None:
    row = normalize_product_row(
        {
            "country": "KR",
            "brand": "CHANEL",
            "korean_name": "코코 마드모아젤",
            "english_name": "coco mademoiselle",
            "product_type": "오 드 빠르펭",
            "key_ingredients": ["오렌지", "자스민"],
        },
        source="official",
        source_country="KR",
        brand="CHANEL",
        generate_description=False,
    )

    assert row["description"] == ""


def test_normalize_product_row_marks_missing_price() -> None:
    row = normalize_product_row(
        {
            "country": "FR",
            "brand": "DIOR",
            "korean_name": "소바쥬",
            "english_name": "sauvage",
            "product_type": "향수",
        },
        source="fragrantica",
        source_country="FR",
        brand="DIOR",
    )

    assert row["price"] == {"raw": "", "amount": None, "currency": ""}
    assert row["meta"]["price_missing_reason"] == "source_unavailable"


def test_normalize_product_row_does_not_infer_accords_and_keywords_from_notes() -> None:
    row = normalize_product_row(
        {
            "country": "KR",
            "brand": "LUSH",
            "korean_name": "더티",
            "english_name": "dirty",
            "product_type": "향수",
            "key_ingredients": ["스피어민트", "라벤더", "샌달우드"],
            "description": "상쾌한 민트와 허브, 부드러운 우디 잔향이 어우러집니다.",
        },
        source="official",
        source_country="KR",
        brand="LUSH",
    )

    assert row["accords"] == []
    assert row["keywords"] == {"ko": [], "en": []}


def test_deepl_translator_reads_configuration_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    monkeypatch.setenv("DEEPL_API_URL", "https://api-free.deepl.com/v2/translate")

    translator = DeepLTranslator.from_env()

    assert translator.api_key == "test-key"
    assert translator.api_url == "https://api-free.deepl.com/v2/translate"


def test_deepl_translator_reads_configuration_from_dotenv(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    monkeypatch.delenv("DEEPL_API_URL", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DEEPL_API_KEY=dotenv-key\nDEEPL_API_URL=https://deepl.example/v2/translate\n",
        encoding="utf-8",
    )

    translator = DeepLTranslator.from_env(env_path=env_path)

    assert translator.api_key == "dotenv-key"
    assert translator.api_url == "https://deepl.example/v2/translate"


def test_deepl_translator_uses_http_api(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"translations": [{"text": "세련된"}]}

    class FakeSession:
        def post(self, url, *, headers, json, timeout):
            calls.append((url, headers, json, timeout))
            return FakeResponse()

    translator = DeepLTranslator(api_key="key", api_url="https://deepl.test/translate", session=FakeSession())

    assert translator.translate("Sophisticated") == "세련된"
    assert calls == [
        (
            "https://deepl.test/translate",
            {"Authorization": "DeepL-Auth-Key key", "Content-Type": "application/json"},
            {"text": ["Sophisticated"], "source_lang": "EN", "target_lang": "KO"},
            30,
        )
    ]
