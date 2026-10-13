import json
import logging
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseScraper, ProductInfo, clean_price_string

logger = logging.getLogger(__name__)

class TrendyolScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.headers.update({
            "Referer": "https://www.trendyol.com/",
            "Accept-Language": "tr-TR,tr;q=0.9"
        })

    async def extract(self, url: str) -> Optional[ProductInfo]:
        try:
            # ty.gl gibi kısa linkleri çözmek ve anti-bot korumasını aşmak için curl_cffi/httpx
            html = None
            try:
                from curl_cffi.requests import AsyncSession
                async with AsyncSession(impersonate="chrome120") as session:
                    response = await session.get(url, headers=self.headers, allow_redirects=True, timeout=15)
                    if response.status_code == 200:
                        html = response.text
                        final_url = str(response.url)
                    else:
                        logger.warning(f"Trendyol istek status: {response.status_code}")
            except Exception as e:
                logger.debug(f"curl_cffi hatası: {e}")

            if not html:
                import httpx
                async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        html = response.text
                        final_url = str(response.url)

            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            # 1. Yöntem: Schema JSON-LD
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get("@type") == "Product":
                        title = data.get("name")
                        image = data.get("image")
                        if isinstance(image, list) and image:
                            image = image[0]
                        offers = data.get("offers", {})
                        price = offers.get("price") or offers.get("lowPrice")
                        if price and title:
                            cleaned_price = clean_price_string(str(price))
                            if cleaned_price:
                                return ProductInfo(
                                    url=final_url if 'final_url' in locals() else url,
                                    title=title.strip(),
                                    price=cleaned_price,
                                    currency="TL",
                                    image_url=image,
                                    platform="trendyol",
                                    domain="trendyol.com"
                                )
                except Exception:
                    continue

            # 2. Yöntem: HTML Elemanları
            # Başlık
            title_elem = soup.select_one("h1.pr-new-br, .product-container h1, .pr-bx-pr-nm")
            title = title_elem.get_text().strip() if title_elem else None

            # Fiyat: İndirimli fiyat (.prc-dsc) veya normal fiyat (.prc-slg)
            price_elem = soup.select_one(".prc-dsc, .prc-slg, .product-price-container")
            price = clean_price_string(price_elem.get_text()) if price_elem else None

            # Görsel
            image_elem = soup.select_one(".base-product-image img, .gallery-container img, .detail-main-img")
            image_url = None
            if image_elem:
                image_url = image_elem.get("src") or image_elem.get("data-src")

            if title and price:
                return ProductInfo(
                    url=final_url if 'final_url' in locals() else url,
                    title=title,
                    price=price,
                    currency="TL",
                    image_url=image_url,
                    platform="trendyol",
                    domain="trendyol.com"
                )

        except Exception as e:
            logger.error(f"Trendyol kazıma hatası ({url}): {e}")

        return None
