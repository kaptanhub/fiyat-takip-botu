# 🛍️ Telegram E-Ticaret Fiyat Takip Botu

Trendyol, Amazon TR, Hepsiburada ve kullanıcı tanımlı herhangi bir web sitesinin fiyatlarını takip eden, fiyat düşüşlerinde Telegram üzerinden anlık bildirim ve fiyat geçmişi grafiği sunan asenkron Python uygulaması.

---

## ✨ Özellikler

- 🛒 **Popüler Platform Desteği**: Trendyol, Amazon TR, Hepsiburada.
- 🌐 **Özel Site Desteği**: Herhangi bir web sitesi için JSON-LD / OpenGraph otomatik tarama veya CSS seçici tanımlama (`/kural_ekle`).
- ⚡ **Kolay Kullanım**: Sadece ürün linkini Telegram sohbetine atmanız yeterli.
- 🎯 **Hedef Fiyat Alarmı**: Belirli bir fiyatın altına düştüğünde bildirim alma.
- 📈 **Görsel Fiyat Grafiği**: Ürünün geçmiş fiyat hareketlerini gösteren otomatik oluşturulan grafikler (`matplotlib`).
- ⏰ **Otomatik Arka Plan Kontrolü**: `APScheduler` ile belirlenen periyotlarda (örn. 30 dakikada bir) sessizce kontrol eder ve sadece indirim olduğunda haber verir.

---

## 🚀 Hızlı Başlangıç

### 1. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Telegram Bot Token Alın
1. Telegram'da [@BotFather](https://t.me/BotFather) botunu açın.
2. `/newbot` komutunu gönderin ve botunuza bir isim verin.
3. Size verilen `HTTP API Token`'ı kopyalayın.

### 3. `.env` Dosyasını Düzenleyin
`.env` dosyasını açıp kopyaladığınız token'ı yapıştırın:
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
CHECK_INTERVAL_MINUTES=30
DATABASE_PATH=fiyat_takip.db
```

### 4. Botu Başlatın
```bash
python main.py
```

---

## 🤖 Bot Komutları

| Komut | Açıklama |
| :--- | :--- |
| `Link Gönderme` | Herhangi bir ürün linkini yapıştırdığınızda bot otomatik algılar ve takip seçeneklerini sunar. |
| `/listele` | Takip ettiğiniz tüm ürünleri, güncel fiyatları ve aksiyon butonlarını listeler. |
| `/kontrol` | Zamanlayıcıyı beklemeden tüm ürünlerin fiyatlarını hemen şimdi kontrol eder. |
| `/kural_ekle` | Özel bir site için CSS seçici kuralı ekler: `/kural_ekle site.com .fiyat-secici` |
| `/kurallar` | Kayıtlı özel site kurallarını listeler. |
| `/yardim` | Kullanım kılavuzunu görüntüler. |

---

## 🧪 Testleri Çalıştırma
Sistemin veritabanı, grafik motoru ve fiyat ayrıştırıcılarını test etmek için:
```bash
python test_setup.py
```
