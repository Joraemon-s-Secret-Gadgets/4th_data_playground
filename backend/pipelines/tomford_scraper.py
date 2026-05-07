"""Command facade for Tom Ford retail fragrance crawling."""

from pipelines.retail_multibrand_scraper import BRAND_CONFIGS, product_to_local_row


BRAND_CONFIG = BRAND_CONFIGS["tomford"]

__all__ = ["BRAND_CONFIG", "product_to_local_row"]

# End of file.
