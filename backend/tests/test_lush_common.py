from pipelines.lush_common import (
    extract_product_remote_id,
    fetch_rendered_html,
    normalize_review,
    print_json_rows,
)


class FakeDriver:
    def __init__(self):
        self.page_source = "<html><body>rendered</body></html>"
        self.closed = False
        self.urls = []

    def get(self, url):
        self.urls.append(url)

    def quit(self):
        self.closed = True


def test_fetch_rendered_html_uses_driver_factory_and_closes_driver():
    driver = FakeDriver()

    html = fetch_rendered_html("https://example.test", driver_factory=lambda: driver)

    assert html == "<html><body>rendered</body></html>"
    assert driver.urls == ["https://example.test"]
    assert driver.closed


def test_extract_product_remote_id_from_lush_product_url():
    assert extract_product_remote_id("https://www.lush.co.kr/products/view/300?foo=bar") == "300"
    assert extract_product_remote_id("https://www.lush.com/uk/en/p/dirty-perfume/300") == "300"


def test_normalize_review_keeps_shared_review_fields():
    review = normalize_review(
        {
            "id": 1,
            "title": " 더티 후기 ",
            "text": "좋아요\n\n또 살게요",
            "rating": 5,
            "created_at": "2026-05-03T10:13:54Z",
            "user_nickname": "김*",
            "helpful_count": None,
            "selected_options": [{"name": "용량", "value": "100ml"}],
            "media_count": 2,
        }
    )

    assert review == {
        "id": 1,
        "title": "더티 후기",
        "text": "좋아요 또 살게요",
        "rating": 5,
        "created_at": "2026-05-03T10:13:54Z",
        "user_nickname": "김*",
        "helpful_count": 0,
        "selected_options": [{"name": "용량", "value": "100ml"}],
        "media_count": 2,
    }


def test_print_json_rows_handles_review_unicode(capsys):
    print_json_rows([{"reviews": [{"text": "좋아요 💗"}]}])

    captured = capsys.readouterr()
    assert "좋아요 💗" in captured.out
