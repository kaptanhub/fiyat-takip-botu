import re
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from config import DEFAULT_USER_AGENT

@dataclass
class ProductInfo:
    url: str
    title: str
    price: float
    currency: str = "TL"
    image_url: Optional[str] = None
    platform: str = "custom"
    domain: str = ""

def clean_price_string(price_str: Optional[str]) -> Optional[float]:
    """
    Farklı formatlardaki fiyat metinlerini (örn: '1.299,99 TL', '₺1,299.99', '1299 TL')
    temizleyip float değere dönüştürür.
    """
    if not price_str:
        return None
        
    # Temizle: boşluklar, TL, ₺, USD, EUR, vb.
    text = price_str.strip()
    
    # Rakam, nokta ve virgül haricindeki karakterleri temizle
    # Ancak virgül ve noktaları koruyalım
    cleaned = re.sub(r"[^\d,\.]", "", text)
    if not cleaned:
        return None
        
    try:
        # Örnek 1: '1.299,99' (Türkiye formatı: binlik nokta, ondalık virgül)
        if "." in cleaned and "," in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Sadece virgül varsa: '1299,99' veya '1,299'
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                cleaned = parts[0] + "." + parts[1]
            elif len(parts) == 2 and len(parts[1]) == 3:
                # Binlik ayracı olarak virgül '1,299'
                cleaned = parts[0] + parts[1]
            else:
                cleaned = cleaned.replace(",", ".")
        elif "." in cleaned:
            # Sadece nokta varsa: '1.299' (binlik) veya '1299.99' (ondalık)
            parts = cleaned.split(".")
            if len(parts) == 2 and len(parts[1]) == 3:
                # Muhtemelen binlik: 1.299 -> 1299
                cleaned = parts[0] + parts[1]
            # Diğer durumda 1299.99 zaten float uyumlu

        val = float(cleaned)
        return round(val, 2)
    except Exception:
        return None

def extract_domain(url: str) -> str:
    """URL'den ana domain bilgisini çeker (örn: amazon.com.tr)."""
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""

class BaseScraper(ABC):
    def __init__(self):
        self.headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

    @abstractmethod
    async def extract(self, url: str) -> Optional[ProductInfo]:
        """Verilen URL'den ürün bilgilerini ayıklayıp ProductInfo döndürür."""
        pass
