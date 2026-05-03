import pytest

from pipelines.lush_uk_scraper import (
    DEFAULT_URL,
    extract_fragrance_products,
    extract_referenced_products,
    fetch_category,
    scrape_perfume_names_from_html,
)


def test_extract_fragrance_products_from_lush_uk_category_html():
    html = """
    <main>
      <article>
        <a href="/uk/en/p/dirty-perfume">
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


def test_scrape_perfume_names_from_html_adds_uk_country():
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


def test_extract_referenced_products_from_next_data():
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


def test_scrape_perfume_names_from_html_rejects_cloudflare_challenge():
    with pytest.raises(RuntimeError, match="Cloudflare challenge"):
        scrape_perfume_names_from_html("Just a moment... Enable JavaScript and cookies to continue")

    with pytest.raises(RuntimeError, match="Cloudflare challenge"):
        scrape_perfume_names_from_html("<title>잠시만 기다리십시오…</title>challenges.cloudflare.com")


def test_lush_uk_default_url_is_fragrance_category():
    assert DEFAULT_URL == "https://www.lush.com/uk/en/c/fragrances"


def test_fetch_category_can_use_selenium_rendered_html(monkeypatch):
    monkeypatch.setattr(
        "pipelines.lush_uk_scraper.fetch_rendered_html",
        lambda url: f"<html>{url}</html>",
    )

    assert fetch_category(use_selenium=True) == "<html>https://www.lush.com/uk/en/c/fragrances</html>"
