import re
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import db
from scraper.router import router
from scraper.base import clean_price_string, extract_domain
from utils.chart import generate_price_chart
from .keyboards import get_product_action_keyboard, get_tracked_item_keyboard

logger = logging.getLogger(__name__)

URL_REGEX = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıyı karşılar ve botun temel kullanımını açıklar."""
    user = update.effective_user
    if user:
        await db.add_or_update_user(user.id, user.username, user.first_name)

    text = (
        f"👋 Merhaba <b>{user.first_name if user else 'Değerli Kullanıcı'}</b>!\n\n"
        "🛍️ <b>E-Ticaret Fiyat Takip Botuna Hoş Geldiniz!</b>\n\n"
        "Bir ürünün fiyatını takip etmek için tek yapmanız gereken <b>ürün linkini bu sohbete göndermek</b>.\n\n"
        "✨ <b>Özellikler:</b>\n"
        "• 🛒 <b>Trendyol, Amazon TR, Hepsiburada</b> ve dilediğiniz özel siteler\n"
        "• 📉 Fiyat düştüğünde anlık bildirim\n"
        "• 🎯 İsteğe bağlı hedef fiyat belirleme\n"
        "• 📈 Fiyat değişim grafiği görüntüleme\n"
        "• ⚙️ Özel siteler için CSS seçici kuralı ekleme\n\n"
        "📌 <b>Komutlar:</b>\n"
        "/listele - Takip ettiğiniz ürünleri gösterir\n"
        "/kontrol - Ürünlerinizin güncel fiyatlarını şimdi denetler\n"
        "/kural_ekle - Özel bir site için fiyat kuralı tanımlar\n"
        "/kurallar - Kayıtlı özel site kurallarını listeler\n"
        "/yardim - Detaylı yardım ve rehber"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım ve kullanım kılavuzu."""
    text = (
        "📖 <b>Kullanım Kılavuzu</b>\n\n"
        "<b>1. Ürün Ekleme:</b>\n"
        "Takip etmek istediğiniz ürünün URL'sini doğrudan mesaj olarak atın.\n\n"
        "<b>2. Özel Site Kuralı Ekleme:</b>\n"
        "Standart dışı bir sitenin fiyatını takip etmek için:\n"
        "<code>/kural_ekle domain.com css_fiyat_secicisi</code>\n"
        "<i>Örnek:</i> <code>/kural_ekle vatanbilgisayar.com .product-list__price</code>\n\n"
        "<b>3. Hedef Fiyat:</b>\n"
        "Bir ürün takibe alınırken veya /listele menüsünden 🎯 Hedef Fiyat butonuna basıp istediğiniz tutarı yazabilirsiniz.\n\n"
        "<b>4. Fiyat Grafiği:</b>\n"
        "/listele komutuyla gelen ürün kartlarındaki 📈 Fiyat Grafiği butonuna basarak fiyat hareketlerini grafik olarak görebilirsiniz."
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının takip ettiği ürünleri listeler."""
    user = update.effective_user
    trackings = await db.get_user_trackings(user.id)

    if not trackings:
        await update.message.reply_text(
            "📭 Henüz takip ettiğiniz bir ürün bulunmuyor.\n"
            "Takip başlatmak için bir ürün linki gönderebilirsiniz!",
            parse_mode="HTML"
        )
        return

    await update.message.reply_text(
        f"📋 <b>Takip Ettiğiniz Ürünler ({len(trackings)} adet):</b>",
        parse_mode="HTML"
    )

    for item in trackings:
        product_id = item["id"]
        title = item["title"]
        price = float(item["current_price"])
        currency = item.get("currency", "TL")
        platform = item.get("platform", "Özel").capitalize()
        target = item.get("target_price")
        url = item["url"]

        target_text = f"🎯 Hedef Fiyat: <b>{target:,.2f} {currency}</b>" if target else "🎯 Hedef Fiyat: <i>Belirtilmedi (Her düşüşte bildir)</i>"

        caption = (
            f"📦 <b>{title}</b>\n\n"
            f"🏷️ Platform: <b>{platform}</b>\n"
            f"💰 Güncel Fiyat: <b>{price:,.2f} {currency}</b>\n"
            f"{target_text}\n"
        )

        keyboard = get_tracked_item_keyboard(product_id, url)

        try:
            if item.get("image_url"):
                await update.message.reply_photo(
                    photo=item["image_url"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
        except Exception:
            # Fotoğraf yüklenemezse metin olarak gönder
            await update.message.reply_text(
                text=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )

async def check_now_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının ürünlerini anlık olarak kontrol eder."""
    user = update.effective_user
    trackings = await db.get_user_trackings(user.id)

    if not trackings:
        await update.message.reply_text("Takip ettiğiniz ürün bulunmuyor.")
        return

    msg = await update.message.reply_text("⏳ Ürünlerinizin güncel fiyatları kontrol ediliyor...")

    updated_count = 0
    for item in trackings:
        try:
            info = await router.extract_product(item["url"])
            if info and info.price:
                new_p = float(info.price)
                if new_p != float(item["current_price"]):
                    await db.update_product_price(item["id"], new_p)
                    updated_count += 1
        except Exception as e:
            logger.error(f"Anlık kontrol hatası: {e}")

    await msg.edit_text(
        f"✅ Kontrol tamamlandı!\n"
        f"Toplam {len(trackings)} ürün kontrol edildi, {updated_count} ürünün fiyatında değişiklik tespit edildi.\n"
        f"Güncel durum için /listele komutunu kullanabilirsiniz."
    )

async def add_rule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Özel site kuralı ekleme komutu: /kural_ekle domain.com .price-selector [.title-selector]"""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "⚠️ <b>Kullanım Şekli:</b>\n"
            "<code>/kural_ekle &lt;domain&gt; &lt;fiyat_css_secicisi&gt; [baslik_secicisi]</code>\n\n"
            "<i>Örnek:</i>\n"
            "<code>/kural_ekle orneksite.com .product-price .product-name</code>",
            parse_mode="HTML"
        )
        return

    domain = args[0]
    price_selector = args[1]
    title_selector = args[2] if len(args) > 2 else None

    await db.save_custom_rule(domain, price_selector, title_selector)
    await update.message.reply_text(
        f"✅ <b>Kural Başarıyla Kaydedildi!</b>\n\n"
        f"🌐 Domain: <code>{domain}</code>\n"
        f"💰 Fiyat Seçici: <code>{price_selector}</code>\n"
        f"📝 Başlık Seçici: <code>{title_selector or 'Otomatik'}</code>\n\n"
        f"Artık bu siteden bir link gönderdiğinizde fiyat bu kurala göre çekilecektir.",
        parse_mode="HTML"
    )

async def list_rules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kayıtlı özel site kurallarını listeler."""
    rules = await db.list_custom_rules()
    if not rules:
        await update.message.reply_text(
            "Kayıtlı özel site kuralı bulunmuyor.\n"
            "Yeni bir kural eklemek için: <code>/kural_ekle domain.com .fiyat-secici</code>",
            parse_mode="HTML"
        )
        return

    text = "📋 <b>Kayıtlı Özel Site Kuralları:</b>\n\n"
    for r in rules:
        text += (
            f"• <b>{r['domain']}</b>\n"
            f"  Fiyat: <code>{r['price_selector']}</code>\n"
        )
        if r.get("title_selector"):
            text += f"  Başlık: <code>{r['title_selector']}</code>\n"
        text += "\n"

    await update.message.reply_text(text, parse_mode="HTML")

async def message_url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı bir link gönderdiğinde veya hedef fiyat beklerken tetiklenir."""
    user = update.effective_user
    text = update.message.text.strip()

    # Kullanıcıdan bir ürün için hedef fiyat bekleniyor mu?
    if context.user_data.get("awaiting_target_product_id"):
        product_id = context.user_data.pop("awaiting_target_product_id")
        target_val = clean_price_string(text)
        if target_val and target_val > 0:
            await db.add_tracking(user.id, product_id, target_price=target_val)
            product = await db.get_product_by_id(product_id)
            p_title = product["title"] if product else "Ürün"
            await update.message.reply_text(
                f"🎯 <b>Hedef Fiyat Kaydedildi!</b>\n\n"
                f"📦 <b>{p_title}</b>\n"
                f"🎯 Hedef Fiyat: <b>{target_val:,.2f} TL</b>\n\n"
                f"Fiyat bu seviyeye veya altına indiğinde size bildireceğiz!",
                parse_mode="HTML"
            )
            return
        else:
            await update.message.reply_text(
                "⚠️ Geçerli bir tutar algılanamadı. Lütfen sadece sayı olarak girin (örn: <code>1500</code> veya <code>1499.90</code>):",
                parse_mode="HTML"
            )
            context.user_data["awaiting_target_product_id"] = product_id
            return

    # Mesaj içinde URL var mı?
    urls = URL_REGEX.findall(text)
    if not urls:
        await update.message.reply_text(
            "💡 Takip etmek istediğiniz ürünün web bağlantısını (linkini) gönderebilir veya komutları görmek için /yardim yazabilirsiniz."
        )
        return

    target_url = urls[0]
    wait_msg = await update.message.reply_text("🔍 <i>Ürün ve fiyat bilgileri inceleniyor, lütfen bekleyin...</i>", parse_mode="HTML")

    try:
        product_info = await router.extract_product(target_url)

        if not product_info or not product_info.price:
            domain = extract_domain(target_url)
            await wait_msg.edit_text(
                f"⚠️ <b>Ürün Bilgileri Otomatik Çekilemedi!</b>\n\n"
                f"🌐 Site: <code>{domain}</code>\n\n"
                f"Bu site özel bir yapıya sahip olabilir. Fiyat bilgisini çekebilmek için bir CSS seçici kuralı ekleyebilirsiniz:\n"
                f"<code>/kural_ekle {domain} &lt;fiyat_css_secicisi&gt;</code>\n\n"
                f"<i>(Örneğin tarayıcınızda fiyata sağ tıklayıp 'İncele' diyerek sınıf adını alabilirsiniz.)</i>",
                parse_mode="HTML"
            )
            return

        # Ürünü veritabanına ekle / getir
        product = await db.get_or_create_product(
            url=product_info.url,
            platform=product_info.platform,
            domain=product_info.domain,
            title=product_info.title,
            image_url=product_info.image_url,
            price=product_info.price,
            currency=product_info.currency
        )

        product_id = product["id"]
        currency = product_info.currency

        caption = (
            f"✅ <b>Ürün Tespit Edildi!</b>\n\n"
            f"📦 <b>{product_info.title}</b>\n\n"
            f"💰 Güncel Fiyat: <b>{product_info.price:,.2f} {currency}</b>\n"
            f"🏷️ Platform: <b>{product_info.platform.capitalize()}</b>\n\n"
            f"Bu ürünü takibe almak istiyor musunuz?"
        )

        keyboard = get_product_action_keyboard(product_id)

        await wait_msg.delete()

        if product_info.image_url:
            try:
                await update.message.reply_photo(
                    photo=product_info.image_url,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return
            except Exception:
                pass

        await update.message.reply_text(
            text=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Mesaj işleme hatası: {e}")
        await wait_msg.edit_text("❌ Ürün incelenirken bir hata oluştu. Lütfen bağlantıyı kontrol edip tekrar deneyin.")

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buton tıklamalarını işler."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data == "cancel":
        await query.message.delete()
        return

    if data.startswith("track:"):
        product_id = int(data.split(":")[1])
        await db.add_tracking(user_id, product_id)
        product = await db.get_product_by_id(product_id)
        title = product["title"] if product else "Ürün"

        await query.message.reply_text(
            f"🔔 <b>{title}</b> başarıyla takibe alındı!\n"
            f"Fiyatta herhangi bir düşüş olduğunda Telegram üzerinden anında bilgilendirileceksiniz.",
            parse_mode="HTML"
        )

    elif data.startswith("target_prompt:"):
        product_id = int(data.split(":")[1])
        context.user_data["awaiting_target_product_id"] = product_id
        await query.message.reply_text(
            "🎯 <b>Hedef Fiyat Belirleme</b>\n\n"
            "Lütfen ürünün düşmesini beklediğiniz hedef fiyatı yazıp gönderin (örn: <code>1500</code>):",
            parse_mode="HTML"
        )

    elif data.startswith("untrack:"):
        product_id = int(data.split(":")[1])
        await db.remove_tracking(user_id, product_id)
        await query.message.reply_text(
            "🗑️ Ürün takipten çıkarıldı.",
            parse_mode="HTML"
        )

    elif data.startswith("chart:"):
        product_id = int(data.split(":")[1])
        product = await db.get_product_by_id(product_id)
        if not product:
            await query.message.reply_text("Ürün bulunamadı.")
            return

        history = await db.get_price_history(product_id)
        if not history:
            await query.message.reply_text("Bu ürün için henüz yeterli fiyat geçmişi bulunmuyor.")
            return

        chart_buf = generate_price_chart(
            product_title=product["title"],
            history=history,
            currency=product.get("currency", "TL")
        )

        await query.message.reply_photo(
            photo=chart_buf,
            caption=f"📈 <b>{product['title']}</b> için güncel fiyat geçmişi grafiği.",
            parse_mode="HTML"
        )
