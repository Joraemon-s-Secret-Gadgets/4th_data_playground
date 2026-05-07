"""Tests for the Chanel Korea scraper facade and modules."""

from typing import Any

import pytest

from pipelines import chanel_korea_scraper
from pipelines.chanel_korea.category import extract_fragrance_products, extract_product_summary
from pipelines.chanel_korea.detail import extract_product_detail
from pipelines.chanel_korea.fetch import with_page
from pipelines.chanel_korea_scraper import DEFAULT_URL, scrape_perfume_names


def test_extract_product_summary_accepts_perfume_products() -> None:
    assert extract_product_summary("코코 마드모아젤 오 드 빠르펭 레퍼런스 116420") == {
        "korean_name": "코코 마드모아젤 오 드 빠르펭",
        "product_type": "오 드 빠르펭",
    }


def test_extract_product_summary_rejects_body_products() -> None:
    assert extract_product_summary("샹스 오 후레쉬 바디 오일 레퍼런스 136980") is None


def test_extract_fragrance_products_reads_category_cards() -> None:
    html = """
    <article>
      <a href="/kr/fragrance/p/116420/coco-mademoiselle-eau-de-parfum-spray/">
        <img src="/images/t_one/w_0.43,h_0.43,c_crop/q_auto:good,f_auto,fl_lossy,dpr_1.1/w_640/coco.jpg">
        코코 마드모아젤 오 드 빠르펭 레퍼런스 116420
      </a>
      <p>206,000 원</p>
    </article>
    <article>
      <a href="/kr/fragrance/p/136980/chance-eau-fraiche-body-oil/">
        샹스 오 후레쉬 바디 오일 레퍼런스 136980
      </a>
      <p>178,000 원</p>
    </article>
    """

    assert extract_fragrance_products(html) == [
        {
            "country": "KR",
            "brand": "CHANEL",
            "korean_name": "코코 마드모아젤 오 드 빠르펭",
            "english_name": "Coco Mademoiselle Eau De Parfum Spray",
            "product_type": "오 드 빠르펭",
            "product_url": "https://www.chanel.com/kr/fragrance/p/116420/coco-mademoiselle-eau-de-parfum-spray",
            "regular_price": "206,000 원",
            "image_url": "https://www.chanel.com/images/t_one/w_0.43,h_0.43,c_crop/q_auto:good,f_auto,fl_lossy,dpr_1.1/w_640/coco.jpg",
        }
    ]


def test_extract_product_detail_reads_ingredients_and_composition() -> None:
    html = """
    <section>
      <h3>구성</h3>
      <meta property="og:image" content="/images/chanel-product.jpg">
      <p>오렌지 노트와 쟈스민, 로즈 어코드가 어우러집니다.</p>
      <h3>상품 필수 정보</h3>
      <h4>성분 목록</h4>
      <p>에탄올,향료,정제수,리모넨,리날룰</p>
      <p>성분 목록은 변경되거나 수시로 바뀔 수 있습니다.</p>
      <h4>제조국</h4>
      <p>프랑스</p>
    </section>
    """

    assert extract_product_detail(html) == {
        "ingredients": "에탄올,향료,정제수,리모넨,리날룰",
        "key_ingredients": ["오렌지 노트와 쟈스민, 로즈 어코드가 어우러집니다."],
        "image_url": "https://www.chanel.com/images/chanel-product.jpg",
    }


def test_chanel_fetch_module_exposes_page_url_builder() -> None:
    assert with_page("https://www.chanel.com/kr/fragrance/women/c/7x1x1/", 3) == (
        "https://www.chanel.com/kr/fragrance/women/c/7x1x1/page-3/"
    )


def test_scrape_perfume_names_adds_product_detail_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHANEL_KR_MAX_PAGES", "1")
    monkeypatch.setattr(
        chanel_korea_scraper,
        "fetch_category",
        lambda _url: """
        <article>
          <a href="/kr/fragrance/p/116420/coco-mademoiselle-eau-de-parfum-spray/">
            코코 마드모아젤 오 드 빠르펭 레퍼런스 116420
          </a>
          <p>206,000 원</p>
        </article>
        """,
    )
    monkeypatch.setattr(
        chanel_korea_scraper,
        "fetch_product_detail",
        lambda _product_url: {
            "ingredients": "에탄올,향료",
            "key_ingredients": ["오렌지 노트"],
            "image_url": "https://www.chanel.com/images/detail.jpg",
        },
    )

    assert scrape_perfume_names() == [
        {
            "country": "KR",
            "brand": "CHANEL",
            "korean_name": "코코 마드모아젤 오 드 빠르펭",
            "english_name": "Coco Mademoiselle Eau De Parfum Spray",
            "product_type": "오 드 빠르펭",
            "product_url": "https://www.chanel.com/kr/fragrance/p/116420/coco-mademoiselle-eau-de-parfum-spray",
            "regular_price": "206,000 원",
            "image_url": "https://www.chanel.com/images/detail.jpg",
            "ingredients": "에탄올,향료",
            "key_ingredients": ["오렌지 노트"],
        }
    ]


def test_scrape_perfume_names_can_limit_detail_fetches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHANEL_KR_MAX_PAGES", "1")
    monkeypatch.setenv("CHANEL_KR_MAX_DETAIL_PAGES", "1")
    monkeypatch.setattr(
        chanel_korea_scraper,
        "fetch_category",
        lambda _url: """
        <article>
          <a href="/kr/fragrance/p/116420/coco-mademoiselle-eau-de-parfum-spray/">
            코코 마드모아젤 오 드 빠르펭 레퍼런스 116420
          </a>
          <p>206,000 원</p>
        </article>
        <article>
          <a href="/kr/fragrance/p/125530/n5-eau-de-parfum-spray/">
            N°5 오 드 빠르펭 레퍼런스 125530
          </a>
          <p>293,000 원</p>
        </article>
        """,
    )
    monkeypatch.setattr(
        chanel_korea_scraper,
        "fetch_product_detail",
        lambda _product_url: {"ingredients": "에탄올", "key_ingredients": []},
    )

    rows = scrape_perfume_names()

    assert len(rows) == 1
    assert rows[0]["korean_name"] == "코코 마드모아젤 오 드 빠르펭"


def test_scrape_perfume_names_can_keep_partial_rows_after_detail_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHANEL_KR_MAX_PAGES", "1")
    monkeypatch.setenv("CHANEL_KR_ALLOW_PARTIAL_RESULTS", "true")
    monkeypatch.setattr(
        chanel_korea_scraper,
        "fetch_category",
        lambda _url: """
        <article>
          <a href="/kr/fragrance/p/116420/coco-mademoiselle-eau-de-parfum-spray/">
            코코 마드모아젤 오 드 빠르펭 레퍼런스 116420
          </a>
          <p>206,000 원</p>
        </article>
        """,
    )
    monkeypatch.setattr(
        chanel_korea_scraper,
        "fetch_product_detail",
        lambda _product_url: (_ for _ in ()).throw(RuntimeError("blocked")),
    )

    rows = scrape_perfume_names()

    assert rows[0]["ingredients"] == ""
    assert rows[0]["key_ingredients"] == []


def test_chanel_korea_default_url_is_women_fragrance_category() -> None:
    assert DEFAULT_URL == "https://www.chanel.com/kr/fragrance/women/c/7x1x1/"


def test_fetch_category_uses_curl_cffi_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHANEL_KR_USE_SELENIUM", raising=False)
    monkeypatch.delenv("CHANEL_KR_FETCHER", raising=False)
    monkeypatch.setattr(
        chanel_korea_scraper,
        "fetch_curl_cffi_html",
        lambda url: f"<html>{url}</html>",
    )

    assert chanel_korea_scraper.fetch_category() == (
        "<html>https://www.chanel.com/kr/fragrance/women/c/7x1x1/</html>"
    )


def test_fetch_category_can_use_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        encoding = ""
        text = "<html>requests</html>"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setenv("CHANEL_KR_FETCHER", "requests")
    monkeypatch.setattr(
        chanel_korea_scraper,
        "get_with_retries",
        lambda url, **kwargs: FakeResponse(),
    )

    assert chanel_korea_scraper.fetch_category() == "<html>requests</html>"


def test_curl_cffi_fetcher_tries_configured_impersonates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeResponse:
        def __init__(self, status_code: int, text: str) -> None:
            self.status_code = status_code
            self.text = text

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP Error {self.status_code}")

    class FakeCurlRequests:
        @staticmethod
        def get(url: str, *, impersonate: str, headers: dict[str, str], timeout: int) -> FakeResponse:
            calls.append(impersonate)
            if impersonate == "blocked":
                return FakeResponse(403, "")
            return FakeResponse(200, f"<html>{url}</html>")

    monkeypatch.setenv("CHANEL_KR_CURL_IMPERSONATES", "blocked, safari17_2_ios")
    monkeypatch.setitem(__import__("sys").modules, "curl_cffi", type("FakeCurlCffi", (), {"requests": FakeCurlRequests}))

    assert chanel_korea_scraper.fetch_curl_cffi_html("https://example.test") == "<html>https://example.test</html>"
    assert calls == ["blocked", "safari17_2_ios"]


def test_fetch_category_can_use_selenium_rendered_html(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        chanel_korea_scraper,
        "fetch_rendered_html",
        lambda url: f"<html>{url}</html>",
    )

    assert chanel_korea_scraper.fetch_category(use_selenium=True) == (
        "<html>https://www.chanel.com/kr/fragrance/women/c/7x1x1/</html>"
    )


def test_main_does_not_write_empty_scrape_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    output_path = tmp_path / "chanel.json"
    monkeypatch.setenv("CHANEL_KR_OUTPUT_PATH", str(output_path))
    monkeypatch.setattr(chanel_korea_scraper, "scrape_perfume_names", lambda _url: [])

    with pytest.raises(RuntimeError, match="no fragrance rows"):
        chanel_korea_scraper.main()

    assert not output_path.exists()

# End of file.
