"""Tests for refactored external fragrance source import helpers."""

from pipelines.fragrantica.transform import format_fragrantica_rows, parse_semicolon_values


def test_parse_semicolon_values_removes_empty_duplicates() -> None:
    assert parse_semicolon_values("citrus; aromatic; citrus; ; fresh") == ["citrus", "aromatic", "fresh"]


def test_format_fragrantica_rows_maps_notes_to_local_schema() -> None:
    rows = format_fragrantica_rows(
        [
            {
                "brand": "Giorgio Armani",
                "name": "A Milano",
                "release_year": "2021",
                "accords": "citrus; aromatic",
                "top_notes": "Citruses; Citron",
                "middle_notes": "Wild Lavender",
                "base_notes": "Orris Root; White Musk",
            }
        ],
        source_url_template="https://www.fragrantica.com/perfume/{brand_slug}/{name_slug}.html",
    )

    assert rows == [
        {
            "country": "IT",
            "korean_name": "",
            "english_name": "A Milano",
            "product_type": "향수",
            "product_url": "https://www.fragrantica.com/perfume/giorgio-armani/a-milano.html",
            "regular_price": "",
            "image_url": "",
            "ingredients": "Released in 2021",
            "key_ingredients": ["Citruses", "Citron", "Wild Lavender", "Orris Root", "White Musk"],
            "keywords": ["citrus", "aromatic"],
        }
    ]

