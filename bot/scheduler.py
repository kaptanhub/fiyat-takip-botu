import logging
import asyncio
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from database.db import db
from scraper.router import router
from config import CHECK_INTERVAL_MINUTES

logger = logging.getLogger(__name__)

async def check_single_product(bot: Bot, product: dict):
    """Tek bir ürünün güncel fiyatını kontrol eder ve indirim varsa bildirim gönderir."""
    product_id = product["id"]
    old_price = float(product["current_price"])
    url = product["url"]
    title = product["title"]
    currency = product.get("currency", "TL")

    try:
        updated_info = await router.extract_product(url)
        if not updated_info or not updated_info.price:
            logger.warning(f"Fiyat kontrolü başarısız ({url})")
            return

        new_price = float(updated_info.price)

        # Fiyat değiştiyse veritabanını güncelle
        if new_price != old_price:
            await db.update_product_price(product_id, new_price)
            logger.info(f"Fiyat değişti [{title}]: {old_price} -> {new_price} {currency}")

            # Eğer fiyat düştüyse takipçilere bildirim yolla
            if new_price < old_price:
                diff = old_price - new_price
                pct = (diff / old_price) * 100
                subscribers = await db.get_product_subscribers(product_id)

                for sub in subscribers:
                    user_id = sub["user_id"]
                    target = sub.get("target_price")
                    notify_any = sub.get("notify_on_any_drop", 1)

                    should_notify = False
                    reason = ""
                    if target and new_price <= float(target):
                        should_notify = True
                        reason = f"🎯 Hedef fiyatınıza ({target:,.2f} {currency}) ulaşıldı!"
                    elif notify_any:
                        should_notify = True
                        reason = "📉 Fiyatta düşüş gerçekleşti!"

                    if should_notify:
                        caption = (
                            f"🔔 <b>FİYAT İNDİRİMİ BİLDİRİMİ!</b>\n\n"
                            f"📦 <b>{title}</b>\n\n"
                            f"🔴 Eski Fiyat: <s>{old_price:,.2f} {currency}</s>\n"
                            f"🟢 <b>Yeni Fiyat: {new_price:,.2f} {currency}</b>\n"
                            f"💥 İndirim: -{diff:,.2f} {currency} (<b>%{pct:.1f}</b>)\n\n"
                            f"{reason}\n\n"
                            f"👉 <a href='{url}'>Ürünü Satın Al / İncele</a>"
                        )

                        try:
                            if product.get("image_url"):
                                await bot.send_photo(
                                    chat_id=user_id,
                                    photo=product["image_url"],
                                    caption=caption,
                                    parse_mode="HTML"
                                )
                            else:
                                await bot.send_message(
                                    chat_id=user_id,
                                    text=caption,
                                    parse_mode="HTML",
                                    disable_web_page_preview=False
                                )
                        except Exception as send_err:
                            logger.error(f"Kullanıcıya bildirim gönderilemedi ({user_id}): {send_err}")

    except Exception as e:
        logger.error(f"Ürün kontrol hatası (ID: {product_id}): {e}")

async def check_all_tracked_products(bot: Bot):
    """Sistemdeki tüm aktif ürünleri periyodik olarak kontrol eder."""
    logger.info("Periyodik fiyat kontrolü başladı...")
    products = await db.get_all_active_products()
    for product in products:
        await check_single_product(bot, product)
        await asyncio.sleep(2)  # Siteleri aşırı yüklememek için bekleme
    logger.info("Periyodik fiyat kontrolü tamamlandı.")

def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Zamanlayıcıyı başlatır."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_all_tracked_products,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        args=[bot],
        id="price_checker",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Fiyat kontrol zamanlayıcısı {CHECK_INTERVAL_MINUTES} dakikalık periyotla başlatıldı.")
    return scheduler
