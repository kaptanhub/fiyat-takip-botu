import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import asyncio
from scraper.base import clean_price_string, extract_domain
from database.db import db
from utils.chart import generate_price_chart

async def run_tests():
    print("[*] Testler Baslatiliyor...\n")

    # 1. Fiyat Temizleme Testleri
    print("1. Fiyat Temizleme Testi:")
    test_cases = [
        ("1.299,99 TL", 1299.99),
        ("TL 450,50", 450.50),
        ("99.90 TL", 99.90),
        ("15.000 TL", 15000.0),
        ("2.499 TL", 2499.0),
    ]
    for raw, expected in test_cases:
        res = clean_price_string(raw)
        status = "[OK]" if res == expected else f"[HATA] (beklenen: {expected}, gelen: {res})"
        print(f"   {raw} -> {res} {status}")

    # 2. Domain Cikarma Testi
    print("\n2. Domain Cikarma Testi:")
    assert extract_domain("https://www.trendyol.com/urun-p-123") == "trendyol.com"
    assert extract_domain("https://amazon.com.tr/dp/B08X") == "amazon.com.tr"
    print("   Domain cikarimi basarili [OK]")

    # 3. Veritabani Testi
    print("\n3. Veritabani Testi:")
    await db.init_db()
    print("   Tablolar olusturuldu [OK]")
    
    # Kullanici ekleme
    await db.add_or_update_user(123456, "testuser", "Test")
    
    # Urun ekleme
    prod = await db.get_or_create_product(
        url="https://example.com/test-product",
        platform="custom",
        domain="example.com",
        title="Test Kulaklik",
        image_url=None,
        price=1000.0,
        currency="TL"
    )
    prod_id = prod["id"]
    print(f"   Urun eklendi (ID: {prod_id}) [OK]")

    # Fiyat gecmisi ekleme
    await db.update_product_price(prod_id, 950.0)
    await db.update_product_price(prod_id, 899.0)

    # Takip ekleme
    await db.add_tracking(123456, prod_id, target_price=900.0)
    user_items = await db.get_user_trackings(123456)
    assert len(user_items) == 1
    print(f"   Kullanici takibi dogrulandi [OK]")

    # 4. Grafik Uretim Testi
    print("\n4. Grafik Uretim Testi:")
    history = await db.get_price_history(prod_id)
    chart_buf = generate_price_chart("Test Kulaklik", history, "TL")
    assert chart_buf.getbuffer().nbytes > 0
    print(f"   Grafik PNG ciktisi basariyla uretildi ({chart_buf.getbuffer().nbytes} bayt) [OK]")

    # 5. Ozel Kural Kaydi Testi
    print("\n5. Ozel Kural Kaydi Testi:")
    await db.save_custom_rule("vatanbilgisayar.com", ".product-price", ".product-name")
    rule = await db.get_custom_rule("vatanbilgisayar.com")
    assert rule["price_selector"] == ".product-price"
    print("   Ozel site kurali kaydedildi ve okundu [OK]")

    print("\n[SUCCESS] TUM ALTYAPI TESTLERI BASARIYLA TAMAMLANDI!")

if __name__ == "__main__":
    asyncio.run(run_tests())
