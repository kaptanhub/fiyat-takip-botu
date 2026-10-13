import logging
from typing import Optional
from .base import BaseScraper, ProductInfo, extract_domain
from .trendyol import TrendyolScraper
from .amazon import AmazonScraper
from .hepsiburada import HepsiburadaScraper
from .generic import GenericScraper

logger = logging.getLogger(__name__)

class ScraperRouter:
    def __init__(self):
        self.trendyol = TrendyolScraper()
        self.amazon = AmazonScraper()
        self.hepsiburada = HepsiburadaScraper()
        self.generic = GenericScraper()

    def get_scraper(self, url: str) -> BaseScraper:
        domain = extract_domain(url).lower()
        
        if "trendyol.com" in domain or "ty.gl" in domain:
            return self.trendyol
        elif "amazon" in domain or "amzn" in domain:
            return self.amazon
        elif "hepsiburada.com" in domain:
            return self.hepsiburada
        else:
            return self.generic

    async def extract_product(self, url: str) -> Optional[ProductInfo]:
        """URL'yi uygun scraper'a yönlendirir ve bilgileri çeker."""
        scraper = self.get_scraper(url)
        try:
            result = await scraper.extract(url)
            # Eğer özel scraper başarısız olduysa ve generic değilse, generic ile bir şans daha verelim
            if not result and not isinstance(scraper, GenericScraper):
                logger.info(f"Özel scraper sonuç vermedi, GenericScraper deneniyor: {url}")
                result = await self.generic.extract(url)
            return result
        except Exception as e:
            logger.error(f"Router üzerinden kazıma hatası ({url}): {e}")
            return None

router = ScraperRouter()
