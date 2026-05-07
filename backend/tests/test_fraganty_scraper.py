"""Tests for Fraganty parser, transform, and scraper facade modules."""

from typing import Any

from pipelines import bvlgari_fraganty_scraper
from pipelines.fraganty.category import extract_perfume_links, perfume_name_from_url
from pipelines.fraganty.detail import extract_perfume_detail, extract_review_detail
from pipelines.fraganty.transform import format_final_rows, refine_raw_details


def test_extract_perfume_links_normalizes_unique_product_urls() -> None:
    html = """
    <a class="group block" href="/perfume/omnia-crystalline?utm=1">Omnia</a>
    <a class="group block" href="/perfume/omnia-crystalline">Duplicate</a>
    <a class="group block" href="/goto/partner">Ad</a>
    """

    assert extract_perfume_links(html) == ["https://fraganty.ai/perfume/omnia-crystalline"]


def test_perfume_name_from_url_reads_slug() -> None:
    assert perfume_name_from_url("https://fraganty.ai/perfume/bvlgari-man-in-black") == "bvlgari man in black"


def test_extract_perfume_detail_reads_fraganty_sections() -> None:
    html = """
    <h1>Bvlgari Omnia Crystalline</h1>
    <div class="perfume-img-bg"><img src="https://img.fraganty.ai/perfume/152.jpg"></div>
    <h2>Main Accords</h2>
    <div>
      <a class="group"><span class="w-24">Woody</span><span class="tabular-nums">86%</span></a>
      <a class="group"><span class="w-24">Floral</span><span class="tabular-nums">74%</span></a>
    </div>
    <span>Top Notes</span><div><span class="flex-1">Bamboo</span><span class="flex-1">Pear</span></div>
    <span>Heart Notes</span><div><span class="flex-1">Lotus</span></div>
    <span>Base Notes</span><div><span class="flex-1">Musk</span></div>
    <h3>Best Season</h3><div class="grid-cols-4">
      <p class="font-semibold">20%</p><p class="font-semibold">82%</p>
      <p class="font-semibold">73%</p><p class="font-semibold">44%</p>
    </div>
    <h3>Day & Night</h3><div class="grid-cols-2">
      <p class="font-semibold">71%</p><p class="font-semibold">29%</p>
    </div>
    """

    assert extract_perfume_detail(html, brand="Bvlgari", url="https://fraganty.ai/perfume/omnia-crystalline") == {
        "brand": "Bvlgari",
        "url": "https://fraganty.ai/perfume/omnia-crystalline",
        "name": "omnia crystalline",
        "image_url": "https://img.fraganty.ai/perfume/152.jpg",
        "main_accords": [
            {"accord": "Woody", "percentage": "86%"},
            {"accord": "Floral", "percentage": "74%"},
        ],
        "notes": {"Top": ["Bamboo", "Pear"], "Heart": ["Lotus"], "Base": ["Musk"]},
        "usage_stats": {
            "Season": {"Winter": "20%", "Spring": "82%", "Summer": "73%", "Fall": "44%"},
            "Time": {"Day": "71%", "Night": "29%"},
        },
        "first_impression": "N/A",
        "scent_profile": "N/A",
        "status": "Success",
    }


def test_extract_review_detail_reads_multi_paragraph_sections() -> None:
    html = """
    <h2>First Impression</h2>
    <p>Bright opening.</p>
    <p>Clean texture.</p>
    <h3>Scent Profile</h3>
    <p>Soft woods and musk.</p>
    """

    assert extract_review_detail(html) == {
        "first_impression": "Bright opening.\nClean texture.",
        "scent_profile": "Soft woods and musk.",
    }


def test_refine_raw_details_filters_and_reduces_fields() -> None:
    rows = refine_raw_details(
        [
            {
                "status": "Success",
                "url": "https://fraganty.ai/perfume/omnia-crystalline",
                "main_accords": [{"accord": "Woody", "percentage": "86%"}],
                "usage_stats": {
                    "Season": {"Winter": "20%", "Spring": "82%", "Summer": "73%"},
                    "Time": {"Day": "71%", "Night": "29%"},
                },
                "first_impression": "Bright",
                "scent_profile": "Fresh",
            },
            {"status": "Review Skipped (Limit)", "first_impression": "N/A", "scent_profile": "N/A"},
        ]
    )

    assert rows == [
        {
            "status": "Success",
            "url": "https://fraganty.ai/perfume/omnia-crystalline",
            "name": "omnia crystalline",
            "main_accords": ["Woody"],
            "usage_stats": {"Season": ["Spring", "Summer"], "Time": "Day"},
            "first_impression": "Bright",
            "scent_profile": "Fresh",
        }
    ]


def test_format_final_rows_matches_local_json_schema() -> None:
    rows = format_final_rows(
        [
            {
                "url": "https://fraganty.ai/perfume/omnia-crystalline",
                "name": "옴니아 크리스탈린",
                "price_info": {"retail": ["$150"]},
                "image_url": "https://img.fraganty.ai/perfume/152.jpg",
                "notes": {"Top": ["대나무"], "Heart": ["연꽃"], "Base": ["머스크"]},
                "main_accords": ["우디", "플로럴"],
                "ai_analysis": {
                    "moods": [{"en": "Refreshing", "ko": "상쾌한"}],
                    "occasions": [{"en": "Spring Day Out", "ko": "봄날 외출"}],
                },
            }
        ],
        english_rows=[
            {
                "url": "https://fraganty.ai/perfume/omnia-crystalline",
                "name": "omnia crystalline",
                "ai_analysis": {
                    "moods": [{"en": "Refreshing", "ko": "상쾌한"}],
                    "occasions": [{"en": "Spring Day Out", "ko": "봄날 외출"}],
                },
            }
        ],
        brand="Bvlgari",
    )

    assert rows == [
        {
            "source": "fraganty",
            "source_country": "이탈리아",
            "brand": "BVLGARI",
            "korean_name": "옴니아 크리스탈린",
            "english_name": "omnia crystalline",
            "normalized_name": "omnia crystalline",
            "product_type": "perfume",
            "product_subtype": "perfume",
            "product_url": "https://fraganty.ai/perfume/omnia-crystalline",
            "image_url": "https://img.fraganty.ai/perfume/152.jpg",
            "price": {"raw": "$150", "amount": 150, "currency": "USD"},
            "description": "옴니아 크리스탈린은 대나무, 연꽃, 머스크 노트가 중심이며 우디, 플로럴 분위기를 가진 향수입니다.",
            "ingredients_raw": "",
            "notes": ["대나무", "연꽃", "머스크"],
            "accords": ["우디", "플로럴"],
            "keywords": {"ko": ["상쾌한", "봄날 외출"], "en": ["Refreshing", "Spring Day Out"]},
            "meta": {
                "release_year": None,
                "original_product_type": "향수",
                "original_country": "이탈리아",
            },
        }
    ]


def test_bvlgari_scraper_facade_uses_injected_links_and_detail_fetch(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        bvlgari_fraganty_scraper,
        "scrape_perfume_detail",
        lambda brand, url: {"brand": brand, "url": url},
    )

    assert bvlgari_fraganty_scraper.scrape_perfume_names(links=["https://fraganty.ai/perfume/omnia-crystalline"]) == [
        {"brand": "Bvlgari", "url": "https://fraganty.ai/perfume/omnia-crystalline"}
    ]

# End of file.
