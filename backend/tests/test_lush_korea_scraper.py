from pipelines.lush_korea_scraper import scrape_perfume_names


def test_scrape_perfume_names_from_live_lush_korea_homepage():
    rows = scrape_perfume_names()
    rows_by_korean_name = {row["korean_name"]: row for row in rows}

    assert rows
    assert all(row["country"] == "KR" for row in rows)
    assert {"더티 보디 스프레이", "트와일라잇 보디 스프레이", "팬지 퍼퓸"} <= set(rows_by_korean_name)

    dirty = rows_by_korean_name["더티 보디 스프레이"]
    assert dirty["english_name"] == "Dirty"
    assert dirty["product_url"] == "https://www.lush.co.kr/products/view/246"
