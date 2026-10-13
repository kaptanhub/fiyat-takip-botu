from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_product_action_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Yeni eklenen ürün için onay ve seçenek butonları."""
    keyboard = [
        [
            InlineKeyboardButton("🔔 Takibe Al", callback_data=f"track:{product_id}"),
            InlineKeyboardButton("🎯 Hedef Fiyat Belirle", callback_data=f"target_prompt:{product_id}")
        ],
        [
            InlineKeyboardButton("❌ İptal", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tracked_item_keyboard(product_id: int, product_url: str) -> InlineKeyboardMarkup:
    """Listelenen ürün kartı için aksiyon butonları."""
    keyboard = [
        [
            InlineKeyboardButton("📈 Fiyat Grafiği", callback_data=f"chart:{product_id}"),
            InlineKeyboardButton("🎯 Hedef Fiyat", callback_data=f"target_prompt:{product_id}")
        ],
        [
            InlineKeyboardButton("🔗 Ürüne Git", url=product_url),
            InlineKeyboardButton("🗑️ Takibi Bırak", callback_data=f"untrack:{product_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
