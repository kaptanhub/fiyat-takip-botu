import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import logging
import asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from config import TELEGRAM_BOT_TOKEN
from database.db import db
from bot.handlers import (
    start_handler,
    help_handler,
    list_handler,
    check_now_handler,
    add_rule_handler,
    list_rules_handler,
    message_url_handler,
    callback_query_handler
)
from bot.scheduler import start_scheduler

# Loglama yapılandırması
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_ping_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Render.com ve UptimeRobot için hafif HTTP yanıtı döndürür."""
    try:
        await reader.read(1024)
        body = "Bot is running 24/7 on Render! 🚀"
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            f"Content-Length: {len(body.encode('utf-8'))}\r\n"
            "Connection: close\r\n\r\n"
            f"{body}"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        logger.debug(f"Ping istemcisi hatası: {e}")

async def post_init(application):
    """Bot ayağa kalktığında veritabanını, zamanlayıcıyı ve Render web sunucusunu başlatır."""
    logger.info("Veritabanı tabloları hazırlanıyor...")
    await db.init_db()
    logger.info("Veritabanı hazır.")

    # Fiyat kontrol zamanlayıcısını başlat
    start_scheduler(application.bot)
    logger.info("Fiyat kontrol zamanlayıcısı başlatıldı.")

    # Render.com ve UptimeRobot için dahili HTTP web sunucusunu başlat
    port = int(os.getenv("PORT", "10000"))
    try:
        server = await asyncio.start_server(handle_ping_client, "0.0.0.0", port)
        logger.info(f"Render Uptime HTTP sunucusu port {port} üzerinde başarıyla başlatıldı.")
    except Exception as e:
        logger.warning(f"HTTP sunucusu başlatılamadı (yerel çalıştırmada normal olabilir): {e}")

def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n" + "=" * 60)
        print("⚠️  UYARI: TELEGRAM_BOT_TOKEN bulunamadı!")
        print("Lütfen .env dosyasını açıp Telegram Bot Token bilginizi ekleyin.")
        print("Token almak için: Telegram'da @BotFather ile konuşup /newbot deyin.")
        print("=" * 60 + "\n")
        sys.exit(1)

    print("🚀 Fiyat Takip Botu başlatılıyor...")

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Komut işleyicileri
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler(["yardim", "help"], help_handler))
    application.add_handler(CommandHandler("listele", list_handler))
    application.add_handler(CommandHandler("kontrol", check_now_handler))
    application.add_handler(CommandHandler("kural_ekle", add_rule_handler))
    application.add_handler(CommandHandler("kurallar", list_rules_handler))

    # Mesaj ve buton işleyicileri
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_url_handler))
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    # Botu çalıştır
    application.run_polling()

if __name__ == "__main__":
    main()
