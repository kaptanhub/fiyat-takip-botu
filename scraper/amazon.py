import logging
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseScraper, ProductInfo, clean_price_string

logger = logging.getLogger(__name__)

class AmazonScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.headers.update({
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.amazon.com.tr/",
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
                logger.debug(f"Amazon curl_cffi denemesi: {e}")

            if not html:
                import httpx
                async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        html = response.text

            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            # Başlık
            title_elem = soup.select_one("#productTitle")
            if not title_elem:
                return None
            title = title_elem.get_text().strip()

            # Fiyat
            price_selectors = [
                "#corePrice_feature_div .a-price .a-offscreen",
                "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
                "#apex_desktop .a-price .a-offscreen",
                "#priceblock_ourprice",
                "#priceblock_dealprice",
                ".a-price .a-offscreen"
            ]

            price = None
            for sel in price_selectors:
                elem = soup.select_one(sel)
                if elem:
                    p = clean_price_string(elem.get_text())
                    if p and p > 0:
                        price = p
                        break

            if not price:
                return None

            # Görsel
            image_elem = soup.select_one("#landingImage, #imgBlkFront, #main-image")
            image_url = None
            if image_elem:
                image_url = image_elem.get("data-old-hires") or image_elem.get("src")

            return ProductInfo(
                url=url,
                title=title,
                price=price,
                currency="TL",
                image_url=image_url,
                platform="amazon",
                domain="amazon.com.tr"
            )

        except Exception as e:
            logger.error(f"Amazon kazıma hatası ({url}): {e}")

        return None
