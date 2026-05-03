from pipelines.lush_korea_scraper import scrape_perfume_names


def test_scrape_perfume_names_from_live_lush_korea_homepage():
    rows = scrape_perfume_names()
    names = {row["name"] for row in rows}

    assert rows
    assert all(row["country"] == "KR" for row in rows)
    assert {"더티", "트와일라잇", "팬지"} <= names
