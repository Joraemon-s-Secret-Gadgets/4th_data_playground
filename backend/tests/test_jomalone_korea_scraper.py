"""Tests for the Jo Malone Korea scraper facade and modules."""

from typing import Any

from pipelines import jomalone_korea_scraper
from pipelines.jomalone_korea.category import extract_fragrance_products
from pipelines.jomalone_korea.detail import extract_product_detail
from pipelines.jomalone_korea_scraper import DEFAULT_URL, scrape_perfume_names


def test_extract_fragrance_products_reads_cologne_cards() -> None:
    html = """
    <div class="elc-grid-item-product">
      <a href="/product/25946/23540/colognes/blackberry-bay-cologne">
        <picture><source srcset="/media/export/cms/products/1000x1000/jo_sku_L32R01_1000x1000_0.png"></picture>
      </a>
      <a href="/product/25946/23540/colognes/blackberry-bay-cologne">
        <h2 data-test-id="product_name">Blackberry &amp; Bay Cologne</h2>
      </a>
      <div class="js-size">100ml</div>
    </div>
    <div class="elc-grid-item-product">
      <a href="/product/25969/12847/home/english-pear-freesia-scented-candle"></a>
      <h2 data-test-id="product_name">English Pear &amp; Freesia Scented Candle</h2>
    </div>
    """

    assert extract_fragrance_products(html) == [
        {
            "country": "KR",
            "korean_name": "",
            "english_name": "Blackberry & Bay Cologne",
            "product_type": "코롱",
            "product_url": "https://www.jomalone.co.kr/product/25946/23540/colognes/blackberry-bay-cologne",
            "regular_price": "",
            "image_url": "https://www.jomalone.co.kr/media/export/cms/products/1000x1000/jo_sku_L32R01_1000x1000_0.png",
            "size": "100ml",
        }
    ]


def test_extract_product_detail_reads_json_ld_and_tasting_notes() -> None:
    html = """
    <html>
      <head>
        <title>블랙베리 앤 베이 코롱 | 조 말론 런던</title>
        <script type="application/ld+json">
        {
          "@context": "http://schema.org/",
          "@type": "ProductGroup",
          "name": "Blackberry & Bay Cologne",
          "image": "/media/default.png",
          "description": "블랙베리를 따던 어린 날의 추억",
          "url": "https://www.jomalone.co.kr/product/25946/23540/colognes/blackberry-bay-cologne",
          "hasVariant": [
            {
              "@type": "Product",
              "name": "Blackberry & Bay Cologne - 100ml",
              "size": "100ml",
              "image": "/media/blackberry.png",
              "offers": {"priceCurrency": "KRW", "price": 239000}
            }
          ]
        }
        </script>
      </head>
      <body>
        <div class="elc-product-overview-no-accordion">
          순수의 향. 블랙베리를 따던 어린 시절의 추억.
        </div>
        <div class="tasting-notes__content-header">블랙베리</div>
        <div class="tasting-notes__content-header">월계수 잎</div>
      </body>
    </html>
    """

    assert extract_product_detail(html, preferred_size="100ml") == {
        "korean_name": "블랙베리 앤 베이 코롱",
        "english_name": "Blackberry & Bay Cologne",
        "product_type": "코롱",
        "regular_price": "239,000원",
        "image_url": "https://www.jomalone.co.kr/media/blackberry.png",
        "ingredients": "순수의 향. 블랙베리를 따던 어린 시절의 추억.",
        "key_ingredients": ["블랙베리", "월계수 잎"],
    }


def test_extract_product_detail_reads_product_offer_list_price() -> None:
    html = """
    <html>
      <head>
        <title>Earl Grey &amp; Cucumber Cologne</title>
        <script type="application/ld+json">
        {
          "@context": "http://schema.org/",
          "@type": "Product",
          "name": "Earl Grey & Cucumber Cologne",
          "image": "/media/earl-grey.png",
          "description": "영국 전통 애프터눈 티에서 영감을 얻은 향.",
          "url": "https://www.jomalone.co.kr/product/25946/15968/colognes/earl-grey-cucumber-cologne",
          "offers": [
            {"@type": "Offer", "priceCurrency": "KRW", "price": 239000}
          ]
        }
        </script>
      </head>
    </html>
    """

    detail = extract_product_detail(html)

    assert detail["regular_price"] == "239,000원"
    assert detail["image_url"] == "https://www.jomalone.co.kr/media/earl-grey.png"


def test_scrape_perfume_names_adds_product_detail_fields(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        jomalone_korea_scraper,
        "fetch_page",
        lambda _url: """
        <div class="elc-grid-item-product">
          <a href="/product/25946/10101/colognes/lime-basil-mandarin-cologne"></a>
          <h2 data-test-id="product_name">Lime Basil &amp; Mandarin Cologne</h2>
          <div class="js-size">100ml</div>
        </div>
        """,
    )
    monkeypatch.setattr(
        jomalone_korea_scraper,
        "fetch_product_detail",
        lambda _url, _size: {
            "korean_name": "라임 바질 앤 만다린 코롱",
            "english_name": "Lime Basil & Mandarin Cologne",
            "product_type": "코롱",
            "regular_price": "239,000원",
            "image_url": "https://www.jomalone.co.kr/media/lime.png",
            "ingredients": "현대적인 감각의 클래식한 향입니다.",
            "key_ingredients": ["만다린", "바질", "앰버우드"],
        },
    )

    assert scrape_perfume_names() == [
        {
            "country": "KR",
            "korean_name": "라임 바질 앤 만다린 코롱",
            "english_name": "Lime Basil & Mandarin Cologne",
            "product_type": "코롱",
            "product_url": "https://www.jomalone.co.kr/product/25946/10101/colognes/lime-basil-mandarin-cologne",
            "regular_price": "239,000원",
            "image_url": "https://www.jomalone.co.kr/media/lime.png",
            "ingredients": "현대적인 감각의 클래식한 향입니다.",
            "key_ingredients": ["만다린", "바질", "앰버우드"],
        }
    ]


def test_jomalone_korea_default_url_is_colognes_category() -> None:
    assert DEFAULT_URL == "https://www.jomalone.co.kr/colognes"

# End of file.
