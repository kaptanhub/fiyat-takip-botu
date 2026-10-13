import json
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from .base import BaseScraper, ProductInfo, clean_price_string, extract_domain
from database.db import db

logger = logging.getLogger(__name__)

class GenericScraper(BaseScraper):
    """
    Herhangi bir web sitesinden ürün bilgilerini çeken esnek scraper.
    JSON-LD, OpenGraph meta etiketleri ve kullanıcı tanımlı CSS kurallarını destekler.
    """

    async def fetch_html(self, url: str) -> Optional[str]:
        """Sayfa kaynak kodunu curl_cffi veya httpx ile çeker."""
        try:
            # Önce gelişmiş TLS taklidi yapan curl_cffi deneyelim
            from curl_cffi.requests import AsyncSession
            async with AsyncSession(impersonate="chrome120") as session:
                response = await session.get(url, headers=self.headers, timeout=15)
                if response.status_code == 200:
                    return response.text
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"curl_cffi isteği başarısız oldu, httpx deneniyor: {e}")

        # Fallback: httpx
        try:
            import httpx
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
        except Exception as e:
            logger.error(f"HTML çekme hatası ({url}): {e}")

        return None

    async def extract(self, url: str) -> Optional[ProductInfo]:
        html = await self.fetch_html(url)
        if not html:
            return None

        domain = extract_domain(url)
        soup = BeautifulSoup(html, "html.parser")

        # 1. Aşama: Veritabanında kayıtlı özel CSS kuralı var mı?
        custom_rule = await db.get_custom_rule(domain)
        if custom_rule:
            product = self._extract_via_custom_rule(soup, url, domain, custom_rule)
            if product:
                return product

        # 2. Aşama: JSON-LD (Schema.org / Product)
        product = self._extract_via_json_ld(soup, url, domain)
        if product:
            return product

        # 3. Aşama: OpenGraph & Meta Etiketleri
        product = self._extract_via_opengraph(soup, url, domain)
        if product:
            return product

        # 4. Aşama: Standart / Yaygın CSS Seçicileri Fallback
        product = self._extract_via_common_selectors(soup, url, domain)
        if product:
            return product

        return None

    def _extract_via_custom_rule(
        self,
        soup: BeautifulSoup,
        url: str,
        domain: str,
        rule: Dict[str, Any]
    ) -> Optional[ProductInfo]:
        """Kullanıcının tanımladığı CSS seçicilerini kullanarak veri çeker."""
        try:
            price_elem = soup.select_one(rule["price_selector"])
            if not price_elem:
                return None
            price = clean_price_string(price_elem.get_text())
            if not price:
                return None

            title = None
            if rule.get("title_selector"):
                title_elem = soup.select_one(rule["title_selector"])
                if title_elem:
                    title = title_elem.get_text().strip()

            if not title:
                title_elem = soup.find("title")
                title = title_elem.get_text().strip() if title_elem else domain

            image_url = None
            if rule.get("image_selector"):
                img_elem = soup.select_one(rule["image_selector"])
                if img_elem:
                    image_url = img_elem.get("src") or img_elem.get("data-src")

            return ProductInfo(
                url=url,
                title=title,
                price=price,
                currency="TL",
                image_url=image_url,
                platform="custom",
                domain=domain
            )
        except Exception as e:
            logger.error(f"Özel kural ile çıkarma hatası: {e}")
            return None

    def _extract_via_json_ld(self, soup: BeautifulSoup, url: str, domain: str) -> Optional[ProductInfo]:
        """Schema.org JSON-LD script etiketlerini ayrıştırır."""
        try:
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                except Exception:
                    continue

                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    item_type = item.get("@type", "")
                    if item_type in ["Product", "IndividualProduct"] or "offers" in item:
                        title = item.get("name")
                        image = item.get("image")
                        if isinstance(image, list) and image:
                            image = image[0]
                        elif isinstance(image, dict):
                            image = image.get("url")

                        offers = item.get("offers")
                        price = None
                        currency = "TL"

                        if isinstance(offers, dict):
                            price = offers.get("price") or offers.get("lowPrice")
                            currency = offers.get("priceCurrency", "TL")
                        elif isinstance(offers, list) and offers:
                            price = offers[0].get("price") or offers[0].get("lowPrice")
                            currency = offers[0].get("priceCurrency", "TL")

                        if price is not None and title:
                            cleaned_price = clean_price_string(str(price))
                            if cleaned_price:
                                return ProductInfo(
                                    url=url,
                                    title=title.strip(),
                                    price=cleaned_price,
                                    currency=currency,
                                    image_url=image,
                                    platform="generic",
                                    domain=domain
                                )
        except Exception as e:
            logger.debug(f"JSON-LD çıkarma hatası: {e}")

        return None

    def _extract_via_opengraph(self, soup: BeautifulSoup, url: str, domain: str) -> Optional[ProductInfo]:
        """OpenGraph ve Schema microdata etiketlerinden bilgi toplar."""
        try:
            # Fiyat
            price_meta = (
                soup.find("meta", property="product:price:amount") or
                soup.find("meta", property="og:price:amount") or
                soup.find("meta", itemprop="price")
            )
            if not price_meta:
                return None

            price_str = price_meta.get("content") or price_meta.get("value")
            price = clean_price_string(price_str)
            if not price:
                return None

            # Para Birimi
            currency_meta = (
                soup.find("meta", property="product:price:currency") or
                soup.find("meta", property="og:price:currency") or
                soup.find("meta", itemprop="priceCurrency")
            )
            currency = currency_meta.get("content", "TL") if currency_meta else "TL"

            # Başlık
            title_meta = soup.find("meta", property="og:title")
            title = title_meta.get("content") if title_meta else None
            if not title:
                title_elem = soup.find("title")
                title = title_elem.get_text().strip() if title_elem else domain

            # Görsel
            img_meta = soup.find("meta", property="og:image")
            image_url = img_meta.get("content") if img_meta else None

            return ProductInfo(
                url=url,
                title=title.strip(),
                price=price,
                currency=currency,
                image_url=image_url,
                platform="generic",
                domain=domain
            )
        except Exception as e:
            logger.debug(f"OpenGraph çıkarma hatası: {e}")

        return None

    def _extract_via_common_selectors(self, soup: BeautifulSoup, url: str, domain: str) -> Optional[ProductInfo]:
        """Sık kullanılan genel CSS seçicilerini tarar."""
        price_selectors = [
            "[itemprop='price']",
            ".product-price",
            ".current-price",
            ".sale-price",
            ".price-current",
            ".price",
            "#price",
            ".fiyat"
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

        # Başlık bul
        title = None
        title_elem = soup.select_one("h1, .product-title, .product-name")
        if title_elem:
            title = title_elem.get_text().strip()
        elif soup.find("title"):
            title = soup.find("title").get_text().strip()
        else:
            title = domain

        # Görsel bul
        image_url = None
        img_elem = soup.select_one(".product-image img, .main-image img, [itemprop='image']")
        if img_elem:
            image_url = img_elem.get("src") or img_elem.get("data-src")

        return ProductInfo(
            url=url,
            title=title,
            price=price,
            currency="TL",
            image_url=image_url,
            platform="generic",
            domain=domain
        )
