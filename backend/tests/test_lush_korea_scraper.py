from pipelines.lush_korea_scraper import DEFAULT_URL, scrape_perfume_names


def test_scrape_perfume_names_from_live_lush_korea_homepage():
    assert DEFAULT_URL == "https://www.lush.co.kr/m/categories/index/56"

    rows = scrape_perfume_names()
    rows_by_korean_name = {row["korean_name"]: row for row in rows}

    assert rows
    assert all(row["country"] == "KR" for row in rows)
    assert {"슬리피 보디 스프레이", "더티 퍼퓸", "팬지 퍼퓸"} <= set(rows_by_korean_name)

    dirty = rows_by_korean_name["더티 퍼퓸"]
    assert dirty["english_name"] == "Dirty"
    assert dirty["product_url"] == "https://www.lush.co.kr/products/view/300"
