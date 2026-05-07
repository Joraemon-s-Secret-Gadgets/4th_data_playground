"""Tests for the Lush UK scraper facade and modules."""

from typing import Any

import pytest

from pipelines.lush_uk.detail import extract_product_detail as extract_uk_detail
from pipelines.lush_uk.search import extract_search_products as extract_uk_search_products
from pipelines.lush_uk_scraper import (
    DEFAULT_URL,
    extract_fragrance_products,
    extract_product_detail,
    extract_product_price,
    extract_search_products,
    extract_referenced_products,
    fetch_collection_products,
    fetch_category,
    scrape_perfume_names,
    scrape_perfume_names_from_html,
)


def test_extract_fragrance_products_from_lush_uk_category_html() -> None:
    html = """
    <main>
      <article>
        <a href="/uk/en/p/dirty-perfume">
          <img src="/cdn/dirty.jpg">
          <h2>Dirty</h2>
          <p>Perfume</p>
        </a>
      </article>
      <article>
        <a href="/uk/en/p/dirty-solidperfume?queryId=abc">
          <h2>Dirty</h2>
          <p>Solid Perfume</p>
        </a>
      </article>
      <article>
        <a href="https://www.lush.com/uk/en/p/sleepy-body-spray">
          <h2>Sleepy</h2>
          <p>Body Spray</p>
        </a>
      </article>
    </main>
    """

    products = extract_fragrance_products(html)

    assert products == [
        {
            "english_name": "Dirty",
            "product_type": "Perfume",
            "product_url": "https://www.lush.com/uk/en/p/dirty-perfume",
            "image_url": "https://www.lush.com/cdn/dirty.jpg",
        },
        {
            "english_name": "Dirty",
            "product_type": "Solid Perfume",
            "product_url": "https://www.lush.com/uk/en/p/dirty-solidperfume",
        },
        {
            "english_name": "Sleepy",
            "product_type": "Body Spray",
            "product_url": "https://www.lush.com/uk/en/p/sleepy-body-spray",
        },
    ]


def test_scrape_perfume_names_from_html_adds_uk_country() -> None:
    rows = scrape_perfume_names_from_html(
        '<a href="/uk/en/p/karma-perfume"><h2>Karma</h2><p>Perfume</p></a>'
    )

    assert rows == [
        {
            "country": "UK",
            "english_name": "Karma",
            "product_type": "Perfume",
            "product_url": "https://www.lush.com/uk/en/p/karma-perfume",
        }
    ]


def test_extract_product_price_reads_visible_sterling_price() -> None:
    html = """
    <span class="sr-only">£30.00</span>
    <button>Add to bag - £30.00</button>
    """

    assert extract_product_price(html) == "£30.00"


def test_extract_product_price_reads_next_data_variant_price() -> None:
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "__APOLLO_STATE__": {
            "ProductVariant:1": {
              "__typename": "ProductVariant",
              "pricing({\\"address\\":{\\"country\\":\\"GB\\"}})": {
                "price": {
                  "gross": {
                    "currency": "GBP",
                    "amount": 70,
                    "fractionDigits": 2
                  }
                }
              }
            },
            "ProductVariant:2": {
              "__typename": "ProductVariant",
              "pricing({\\"address\\":{\\"country\\":\\"GB\\"}})": {
                "price": {
                  "gross": {
                    "currency": "GBP",
                    "amount": 30,
                    "fractionDigits": 2
                  }
                }
              }
            }
          }
        }
      }
    }
    </script>
    """

    assert extract_product_price(html) == "£30.00"


def test_scrape_perfume_names_from_non_default_url_adds_regular_price_from_product_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "pipelines.lush_uk_scraper.fetch_category",
        lambda url: '<a href="/uk/en/p/dirty-perfume"><h2>Dirty</h2><p>Perfume</p></a>',
    )
    monkeypatch.setattr(
        "pipelines.lush_uk_scraper.fetch_product_price",
        lambda url: "£30.00",
    )
    monkeypatch.setattr(
        "pipelines.lush_uk_scraper.fetch_product_detail",
        lambda url: {"ingredients": "Alcohol Denat.", "key_ingredients": ["Mint"]},
    )

    assert scrape_perfume_names("https://www.lush.com/uk/en/c/cruelty-free-perfume") == [
        {
            "country": "UK",
            "english_name": "Dirty",
            "product_type": "Perfume",
            "product_url": "https://www.lush.com/uk/en/p/dirty-perfume",
            "regular_price": "£30.00",
            "image_url": "",
            "ingredients": "Alcohol Denat.",
            "key_ingredients": ["Mint"],
        }
    ]


def test_extract_search_products_reads_paginated_search_payload() -> None:
    payload = {
        "data": {
            "searchQuery": {
                "items": [
                    {
                        "content": {
                            "name": "Sleepy",
                            "slug": "sleepy-bodyspray",
                            "minPrice": 29,
                            "currency": "GBP",
                            "thumbnail": "https://images.lush.com/sleepy.jpg",
                            "attributes": {"type": "Body Spray"},
                        }
                    }
                ],
                "pagination": {"nextPage": None},
            }
        }
    }

    assert extract_search_products(payload) == [
        {
            "country": "UK",
            "english_name": "Sleepy",
            "product_type": "Body Spray",
            "product_url": "https://www.lush.com/uk/en/p/sleepy-bodyspray",
            "regular_price": "£29.00",
            "image_url": "https://images.lush.com/sleepy.jpg",
        }
    ]


def test_uk_search_module_exposes_search_product_extraction() -> None:
    payload = {
        "data": {
            "searchQuery": {
                "items": [
                    {
                        "content": {
                            "name": "Dirty",
                            "slug": "dirty-perfume",
                            "minPrice": 30,
                            "currency": "GBP",
                            "thumbnail": "https://images.lush.com/dirty.jpg",
                            "attributes": {"type": "Perfume"},
                        }
                    }
                ]
            }
        }
    }

    assert extract_uk_search_products(payload)[0]["product_url"] == (
        "https://www.lush.com/uk/en/p/dirty-perfume"
    )


def test_fetch_collection_products_follows_search_pagination() -> None:
    class FakeResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

    class FakeSession:
        def __init__(self) -> None:
            self.pages: list[int] = []

        def post(
            self,
            _url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, str],
            timeout: int,
        ) -> FakeResponse:
            page = json["variables"]["page"]
            self.pages.append(page)
            return FakeResponse(
                {
                    "data": {
                        "searchQuery": {
                            "items": [
                                {
                                    "content": {
                                        "name": f"Product {page}",
                                        "slug": f"product-{page}",
                                        "minPrice": page,
                                        "currency": "GBP",
                                        "attributes": {"type": "Perfume"},
                                    }
                                }
                            ],
                            "pagination": {"nextPage": page + 1 if page == 1 else None},
                        }
                    }
                }
            )

    session = FakeSession()

    rows = fetch_collection_products("Perfumes", session=session, per_page=1)

    assert session.pages == [1, 2]
    assert [row["english_name"] for row in rows] == ["Product 1", "Product 2"]


def test_extract_product_detail_reads_next_data_ingredients() -> None:
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "__APOLLO_STATE__": {
            "Product:1": {
              "__typename": "Product",
              "thumbnail": {"url": "https://images.lush.com/dirty.jpg"},
              "attributes": [
                {
                  "attribute": {"slug": "ingredients"},
                  "values": [
                    {"name": "Alcohol Denat."},
                    {"name": "Mentha Spicata Herb Oil (Spearmint Oil)"}
                  ]
                },
                {
                  "attribute": {"slug": "key_ingredients"},
                  "values": [
                    {"name": "Mint"},
                    {"name": "Neroli"}
                  ]
                }
              ]
            }
          }
        }
      }
    }
    </script>
    """

    assert extract_product_detail(html) == {
        "ingredients": "Alcohol Denat., Mentha Spicata Herb Oil (Spearmint Oil)",
        "key_ingredients": ["Mint", "Neroli"],
        "image_url": "https://images.lush.com/dirty.jpg",
    }


def test_extract_product_detail_reads_referenced_product_image() -> None:
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "__APOLLO_STATE__": {
            "ProductImage:1": {
              "__typename": "ProductImage",
              "url": "https://images.lush.com/dirty-large.jpg"
            },
            "Product:1": {
              "__typename": "Product",
              "images": [{"__ref": "ProductImage:1"}],
              "attributes": []
            }
          }
        }
      }
    }
    </script>
    """

    assert extract_product_detail(html)["image_url"] == "https://images.lush.com/dirty-large.jpg"


def test_uk_detail_module_exposes_product_detail_extraction() -> None:
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"__APOLLO_STATE__":{"Product:1":{"__typename":"Product","attributes":[{"attribute":{"slug":"key_ingredients"},"values":[{"name":"Mint"}]}]}}}}}
    </script>
    """

    assert extract_uk_detail(html)["key_ingredients"] == ["Mint"]


def test_scrape_perfume_names_adds_product_detail_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pipelines.lush_uk_scraper.fetch_collection_products",
        lambda _collection_name: [
            {
                "country": "UK",
                "english_name": "Dirty",
                "product_type": "Perfume",
                "product_url": "https://www.lush.com/uk/en/p/dirty-perfume",
                "regular_price": "£30.00",
            }
        ],
    )
    monkeypatch.setattr(
        "pipelines.lush_uk_scraper.fetch_product_detail",
        lambda _product_url: {
            "ingredients": "Alcohol Denat., Parfum",
            "key_ingredients": ["Mint"],
        },
    )

    assert scrape_perfume_names() == [
        {
            "country": "UK",
            "english_name": "Dirty",
            "product_type": "Perfume",
            "product_url": "https://www.lush.com/uk/en/p/dirty-perfume",
            "regular_price": "£30.00",
            "image_url": "",
            "ingredients": "Alcohol Denat., Parfum",
            "key_ingredients": ["Mint"],
        }
    ]


def test_extract_referenced_products_from_next_data() -> None:
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "__APOLLO_STATE__": {
            "AttributeValue:1": {
              "__typename": "AttributeValue",
              "name": "Dirty",
              "slug": "123_799",
              "reference": "UHJvZHVjdDo3OTk="
            },
            "AttributeValue:2": {
              "__typename": "AttributeValue",
              "name": "Dirty",
              "slug": "1126_1099",
              "reference": "UHJvZHVjdDoxMDk5"
            }
          }
        }
      }
    }
    </script>
    """

    products = extract_referenced_products(html)

    assert products == [
        {
            "english_name": "Dirty",
            "product_type": "Perfume",
            "product_url": "https://www.lush.com/uk/en/p/dirty-perfume",
        },
        {
            "english_name": "Dirty",
            "product_type": "Body Spray",
            "product_url": "https://www.lush.com/uk/en/p/dirty-body-spray",
        },
    ]


def test_scrape_perfume_names_from_html_rejects_cloudflare_challenge() -> None:
    with pytest.raises(RuntimeError, match="Cloudflare challenge"):
        scrape_perfume_names_from_html("Just a moment... Enable JavaScript and cookies to continue")

    with pytest.raises(RuntimeError, match="Cloudflare challenge"):
        scrape_perfume_names_from_html("<title>잠시만 기다리십시오…</title>challenges.cloudflare.com")


def test_lush_uk_default_url_is_fragrance_category() -> None:
    assert DEFAULT_URL == "https://www.lush.com/uk/en/c/fragrances"


def test_fetch_category_uses_scrapling_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LUSH_UK_USE_SELENIUM", raising=False)
    monkeypatch.delenv("LUSH_UK_FETCHER", raising=False)
    monkeypatch.setattr(
        "pipelines.lush_uk_scraper.fetch_scrapling_html",
        lambda url: f"<html>{url}</html>",
    )

    assert fetch_category() == "<html>https://www.lush.com/uk/en/c/fragrances</html>"


def test_fetch_category_can_use_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        encoding = ""
        text = "<html>requests</html>"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setenv("LUSH_UK_FETCHER", "requests")
    monkeypatch.setattr(
        "pipelines.lush_uk_scraper.get_with_retries",
        lambda url, **kwargs: FakeResponse(),
    )

    assert fetch_category() == "<html>requests</html>"


def test_fetch_category_can_use_selenium_rendered_html(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pipelines.lush_uk_scraper.fetch_rendered_html",
        lambda url: f"<html>{url}</html>",
    )

    assert fetch_category(use_selenium=True) == "<html>https://www.lush.com/uk/en/c/fragrances</html>"

# End of file.
