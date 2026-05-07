"""Tests for Persona-L crawler export normalization."""

from pipelines.persona_sources import format_persona_rows, parse_byredo_note_lines


def test_parse_byredo_note_lines_extracts_note_values() -> None:
    assert parse_byredo_note_lines(
        [
            "탑 노트: 핑크 페퍼, 터키 장미 꽃잎",
            "하트 노트: 라즈베리 블로썸",
            "베이스 노트: 파피루스, 화이트 앰버",
        ]
    ) == ["핑크 페퍼", "터키 장미 꽃잎", "라즈베리 블로썸", "파피루스", "화이트 앰버"]


def test_format_persona_rows_normalizes_byredo_export() -> None:
    rows = format_persona_rows(
        [
            {
                "brand": "Byredo",
                "name": "팔레르모",
                "size": "50ml",
                "price": 270000,
                "image_url": "https://example.test/byredo.jpg",
                "source_url": "https://www.byredo.com/ko_kr/palermo",
                "description": "지중해의 역사와 문화를 담은 팔레르모 오 드 퍼퓸.",
                "category": "오 드 퍼퓸",
                "family": "시트러스",
                "notes": ["탑 노트: 쁘띠그레인, 베르가못", "베이스 노트: 암브레트"],
            }
        ]
    )

    assert rows == [
        {
            "source": "official",
            "source_country": "KR",
            "brand": "BYREDO",
            "korean_name": "팔레르모",
            "english_name": "",
            "normalized_name": "",
            "product_type": "perfume",
            "product_subtype": "eau_de_parfum",
            "product_url": "https://www.byredo.com/ko_kr/palermo",
            "image_url": "https://example.test/byredo.jpg",
            "price": {"raw": "270,000원", "amount": 270000, "currency": "KRW"},
            "description": "지중해의 역사와 문화를 담은 팔레르모 오 드 퍼퓸.",
            "ingredients_raw": "",
            "notes": ["쁘띠그레인", "베르가못", "암브레트"],
            "accords": ["시트러스"],
            "keywords": {"ko": [], "en": []},
            "meta": {
                "release_year": None,
                "original_product_type": "오 드 퍼퓸",
                "original_country": "KR",
            },
        }
    ]


def test_format_persona_rows_normalizes_nagchampa_keywords() -> None:
    rows = format_persona_rows(
        [
            {
                "brand": "Nag Champa",
                "name": "시그니처 나그참파",
                "size": "15g",
                "price": 12000,
                "image_url": "https://example.test/nag.jpg",
                "source_url": "https://nagchampa.co.kr/product/detail.html?product_no=1",
                "category": "인센스 스틱",
                "keywords": ["명상", "정화", "차분함"],
            }
        ]
    )

    assert rows[0]["brand"] == "NAG CHAMPA"
    assert rows[0]["product_subtype"] == "incense_stick"
    assert rows[0]["keywords"] == {"ko": [], "en": []}
    assert rows[0]["description"] == "시그니처 나그참파 향수입니다."
