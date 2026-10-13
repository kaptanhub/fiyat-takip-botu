import json
import logging
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseScraper, ProductInfo, clean_price_string

logger = logging.getLogger(__name__)

class HepsiburadaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.headers.update({
            "Referer": "https://www.hepsiburada.com/",
            "Accept-Language": "tr-TR,tr;q=0.9"
        })

    async def extract(self, url: str) -> Optional[ProductInfo]:
        try:
            html = None
            try:
                from curl_cffi.requests import AsyncSession
                async with AsyncSession(impersonate="chrome120") as session:
                    response = await session.get(url, headers=self.headers, allow_redirects=True, timeout=15)
                    if response.status_code == 200:
                        html = response.text
            except Exception as e:
                logger.debug(f"Hepsiburada curl_cffi: {e}")

            if not html:
                import httpx
                async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        html = response.text

            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            # 1. Yöntem: JSON-LD
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            title = item.get("name")
                            image = item.get("image")
                            if isinstance(image, list) and image:
                                image = image[0]
                            offers = item.get("offers", {})
                            price = offers.get("price") or offers.get("lowPrice")
                            if price and title:
                                cleaned_price = clean_price_string(str(price))
                                if cleaned_price:
                                    return ProductInfo(
                                        url=url,
                                        title=title.strip(),
                                        price=cleaned_price,
                                        currency="TL",
                                        image_url=image,
                                        platform="hepsiburada",
                                        domain="hepsiburada.com"
                                    )
                except Exception:
                    continue

            # 2. Yöntem: HTML Elemanları
            title_elem = soup.select_one("h1#product-name, [data-test-id='title'], h1")
            title = title_elem.get_text().strip() if title_elem else None

            price_selectors = [
                "[data-test-id='price-current-price']",
                "[data-test-id='default-price']",
                "#offering-price",
                "[itemprop='price']",
                ".price"
            ]
            price = None
            for sel in price_selectors:
                elem = soup.select_one(sel)
                if elem:
                    p = clean_price_string(elem.get_text())
                    if p and p > 0:
                        price = p
                        break

            image_elem = soup.select_one("[data-test-id='product-image'] img, .product-image img, [itemprop='image']")
            image_url = None
            if image_elem:
                image_url = image_elem.get("src") or image_elem.get("data-src")

            if title and price:
                return ProductInfo(
                    url=url,
                    title=title,
                    price=price,
                    currency="TL",
                    image_url=image_url,
                    platform="hepsiburada",
                    domain="hepsiburada.com"
                )

        except Exception as e:
            logger.error(f"Hepsiburada kazıma hatası ({url}): {e}")

        return None
