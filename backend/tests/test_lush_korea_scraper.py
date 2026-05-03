from pipelines.lush_korea_scraper import DEFAULT_URL, print_json_rows, scrape_perfume_names


def test_print_json_rows_handles_review_unicode(capsys):
    print_json_rows([{"reviews": [{"text": "좋아요 💗"}]}])

    captured = capsys.readouterr()
    assert "좋아요 💗" in captured.out


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
    assert "변성알코올" in dirty["ingredients"]
    assert "스피어민트" in dirty["key_ingredients"]
    assert dirty["review_count"] == len(dirty["reviews"])
    assert dirty["review_count"] > 0
    assert {"id", "title", "text", "rating", "created_at", "user_nickname"} <= set(dirty["reviews"][0])
