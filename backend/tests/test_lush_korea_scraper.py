"""Tests for the Lush Korea scraper facade and modules."""

from typing import Any

import pytest
import requests

from pipelines import lush_korea_scraper
from pipelines.lush_korea.detail import extract_product_detail as extract_kr_detail
from pipelines.lush_korea.fetch import with_page as kr_with_page
from pipelines.lush_korea_scraper import (
    DEFAULT_URL,
    extract_homepage_fragrance_products,
    extract_product_detail,
    fetch_homepage,
    find_product_metadata,
    scrape_perfume_names,
)


class FakeElement:
    pass


class FakeDriver:
    page_source = "<html>loaded</html>"

    def __init__(self) -> None:
        self.loaded_url = ""
        self.scripts: list[str] = []
        self.quit_called = False
        self._counts = iter([2, 4, 4, 4])

    def get(self, url: str) -> None:
        self.loaded_url = url

    def execute_script(self, script: str) -> None:
        self.scripts.append(script)

    def find_elements(self, by: str, selector: str) -> list[FakeElement]:
        return [FakeElement() for _ in range(next(self._counts))]

    def quit(self) -> None:
        self.quit_called = True


def test_fetch_homepage_scrolls_until_product_count_is_stable() -> None:
    driver = FakeDriver()

    html = fetch_homepage(
        "https://example.test/category",
        driver_factory=lambda: driver,
        sleep=lambda _seconds: None,
        stable_iterations=2,
    )

    assert html == "<html>loaded</html>"
    assert driver.loaded_url == "https://example.test/category"
    assert driver.scripts == [
        "window.scrollTo(0, document.body.scrollHeight);",
        "window.scrollTo(0, document.body.scrollHeight);",
        "window.scrollTo(0, document.body.scrollHeight);",
        "window.scrollTo(0, document.body.scrollHeight);",
    ]
    assert driver.quit_called


def test_fetch_homepage_uses_static_request_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        text = "<html>static</html>"
        encoding = ""

        def raise_for_status(self) -> None:
            return None

    monkeypatch.delenv("LUSH_KR_USE_SELENIUM", raising=False)
    monkeypatch.setattr(
        lush_korea_scraper,
        "_get_with_retries",
        lambda url, **kwargs: FakeResponse(),
    )

    assert fetch_homepage("https://example.test/category") == "<html>static</html>"


def test_korea_fetch_module_exposes_page_url_builder() -> None:
    assert kr_with_page("https://www.lush.co.kr/m/categories/index/56?sort=popularity", 3) == (
        "https://www.lush.co.kr/m/categories/index/56?sort=popularity&page=3"
    )


class FakeSearchResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.encoding = ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error")

    def json(self) -> dict[str, Any]:
        return self._payload


def test_find_product_metadata_tries_next_query_after_search_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_get_with_retries(_session: Any, _url: str, *, params: dict[str, str], timeout: int) -> FakeSearchResponse:
        calls.append(params["query"])
        if params["query"] == "솔티 보디 스프레이":
            return FakeSearchResponse(500, {})
        return FakeSearchResponse(
            200,
            {
                "info": {
                    "item": [
                        {
                            "itemName": "솔티",
                            "itemRange": "보디 스프레이",
                            "itemEName": "Salty",
                            "itemUserCode": "999",
                        }
                    ]
                }
            },
        )

    monkeypatch.setattr(lush_korea_scraper, "_get_with_retries", fake_get_with_retries)

    metadata = find_product_metadata(requests.Session(), "솔티", "보디 스프레이")

    assert calls == ["솔티 보디 스프레이", "솔티"]
    assert metadata == {
        "english_name": "Salty",
        "product_url": "https://www.lush.co.kr/products/view/999",
        "regular_price": "",
    }


def test_extract_homepage_fragrance_products_keeps_product_url_from_category_card() -> None:
    html = """
    <li class="prdlist__item">
      <a href="/products/view/G21000004883">
        <img src="/upload/item/G21000004883.png">
        <span class="prdlist__item__tit">비틀 100ml</span>
        <span class="prdlist__item__category">퍼퓸</span>
        <span class="prdlist__item__price">70,000원</span>
      </a>
    </li>
    """

    assert extract_homepage_fragrance_products(html) == [
        {
            "korean_name": "비틀 100ml",
            "product_type": "퍼퓸",
            "product_url": "https://www.lush.co.kr/products/view/G21000004883",
            "regular_price": "70,000원",
            "image_url": "https://www.lush.co.kr/upload/item/G21000004883.png",
        }
    ]


def test_extract_homepage_fragrance_products_normalizes_javascript_product_url() -> None:
    html = """
    <li class="prdlist__item">
      <a href="javascript:moveProductView('/m/products/view/G21000006023?giftYn=Y&dc=standard')">
        <span class="prdlist__item__tit">허니 아이 워시드 더 키즈</span>
        <span class="prdlist__item__category">캔들</span>
      </a>
    </li>
    """

    assert extract_homepage_fragrance_products(html)[0]["product_url"] == (
        "https://www.lush.co.kr/products/view/G21000006023"
    )


def test_extract_product_detail_reads_renewal_all_ingredient_block() -> None:
    html = """
    <div class="all-ingre">
      <p><strong>대표성분</strong> 시더우드 오일, 장미</p>
      <div class="all-ingre">
        <p><strong>전 성분 표기&nbsp;</strong>변성알코올,향료,시더우드오일,장미꽃오일</p>
      </div>
    </div>
    """

    assert extract_product_detail(html) == {
        "ingredients": "변성알코올,향료,시더우드오일,장미꽃오일",
        "key_ingredients": ["시더우드 오일", "장미"],
    }


def test_korea_detail_module_exposes_product_detail_extraction() -> None:
    html = """
    <div class="all-ingre">
      <p><strong>대표성분</strong> 시더우드 오일</p>
    </div>
    """

    assert extract_kr_detail(html)["key_ingredients"] == ["시더우드 오일"]


def test_scrape_perfume_names_uses_category_product_url_when_search_has_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_detail_urls: list[str] = []

    monkeypatch.setattr(
        lush_korea_scraper,
        "fetch_homepage",
        lambda _url: """
        <li class="prdlist__item">
            <a href="/products/view/G21000004883">
              <span class="prdlist__item__tit">비틀 100ml</span>
              <span class="prdlist__item__category">퍼퓸</span>
              <span class="prdlist__item__price">70,000원</span>
            </a>
          </li>
        """,
    )
    monkeypatch.setattr(
        lush_korea_scraper,
        "find_product_metadata",
        lambda _session, _korean_name, _product_type: {"english_name": "", "product_url": ""},
    )

    def fake_fetch_product_detail(_session: Any, product_url: str) -> dict[str, Any]:
        captured_detail_urls.append(product_url)
        return {"ingredients": "변성알코올", "key_ingredients": []}

    monkeypatch.setattr(lush_korea_scraper, "fetch_product_detail", fake_fetch_product_detail)

    rows = scrape_perfume_names()

    assert captured_detail_urls == ["https://www.lush.co.kr/products/view/G21000004883"]
    assert rows[0]["product_url"] == "https://www.lush.co.kr/products/view/G21000004883"
    assert rows[0]["regular_price"] == "70,000원"


def test_find_product_metadata_formats_regular_price_from_search_sale_price(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_with_retries(_session: Any, _url: str, *, params: dict[str, str], timeout: int) -> FakeSearchResponse:
        return FakeSearchResponse(
            200,
            {
                "info": {
                    "item": [
                        {
                            "itemName": "더티",
                            "itemRange": "퍼퓸",
                            "itemEName": "Dirty",
                            "itemUserCode": "300",
                            "salePrice": 70000,
                        }
                    ]
                }
            },
        )

    monkeypatch.setattr(lush_korea_scraper, "_get_with_retries", fake_get_with_retries)

    metadata = find_product_metadata(requests.Session(), "더티", "퍼퓸")

    assert metadata["regular_price"] == "70,000원"


def test_scrape_perfume_names_does_not_fetch_reviews_while_reviews_are_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        lush_korea_scraper,
        "fetch_homepage",
        lambda _url: """
        <li class="prdlist__item">
          <span class="prdlist__item__tit">더티</span>
          <span class="prdlist__item__category">퍼퓸</span>
        </li>
        """,
    )
    monkeypatch.setattr(
        lush_korea_scraper,
        "find_product_metadata",
        lambda _session, _korean_name, _product_type: {
            "english_name": "Dirty",
            "product_url": "https://www.lush.co.kr/products/view/300",
            "regular_price": "70,000원",
        },
    )
    monkeypatch.setattr(
        lush_korea_scraper,
        "fetch_product_detail",
        lambda _session, _product_url: {"ingredients": "변성알코올", "key_ingredients": ["스피어민트"]},
    )

    def fail_if_reviews_are_fetched(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("reviews should be disabled")

    monkeypatch.setattr(lush_korea_scraper, "fetch_product_reviews", fail_if_reviews_are_fetched)

    rows = scrape_perfume_names()

    assert rows == [
        {
            "country": "KR",
            "korean_name": "더티 퍼퓸",
            "english_name": "Dirty",
            "product_type": "퍼퓸",
            "product_url": "https://www.lush.co.kr/products/view/300",
            "regular_price": "70,000원",
            "image_url": "",
            "ingredients": "변성알코올",
            "key_ingredients": ["스피어민트"],
        }
    ]


def test_scrape_perfume_names_from_live_lush_korea_homepage() -> None:
    assert DEFAULT_URL == "https://www.lush.co.kr/m/categories/index/56?sort=popularity"

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
    assert "review_count" not in dirty
    assert "reviews" not in dirty

# End of file.
