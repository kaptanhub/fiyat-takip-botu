import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any
from config import DATABASE_PATH

class Database:
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = str(db_path)

    async def init_db(self):
        """Veritabanı tablolarını oluşturur."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON;")
            
            # Kullanıcılar tablosu
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Takip edilen ürünler tablosu
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    platform TEXT,
                    domain TEXT,
                    title TEXT,
                    image_url TEXT,
                    current_price REAL,
                    currency TEXT DEFAULT 'TL',
                    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Kullanıcı - Ürün takip ilişkisi
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trackings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    product_id INTEGER,
                    target_price REAL,
                    notify_on_any_drop BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
                    UNIQUE(user_id, product_id)
                );
            """)

            # Fiyat geçmişi tablosu
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    price REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
                );
            """)

            # Kullanıcı tanımlı özel site kuralları
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_site_rules (
                    domain TEXT PRIMARY KEY,
                    price_selector TEXT NOT NULL,
                    title_selector TEXT,
                    image_selector TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.commit()

    async def add_or_update_user(self, telegram_id: int, username: Optional[str], first_name: Optional[str]):
        """Kullanıcıyı kaydeder veya günceller."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO users (telegram_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name;
            """, (telegram_id, username, first_name))
            await conn.commit()

    async def get_or_create_product(
        self,
        url: str,
        platform: str,
        domain: str,
        title: str,
        image_url: Optional[str],
        price: float,
        currency: str = "TL"
    ) -> Dict[str, Any]:
        """Ürünü getirir veya yoksa oluşturup fiyat geçmişine ilk kaydı ekler."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM products WHERE url = ?", (url,))
            row = await cursor.fetchone()
            
            if row:
                return dict(row)

            # Yeni ürün ekle
            cursor = await conn.execute("""
                INSERT INTO products (url, platform, domain, title, image_url, current_price, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (url, platform, domain, title, image_url, price, currency))
            product_id = cursor.lastrowid

            # İlk fiyat geçmişi kaydı
            await conn.execute("""
                INSERT INTO price_history (product_id, price)
                VALUES (?, ?)
            """, (product_id, price))

            await conn.commit()

            cursor = await conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            new_row = await cursor.fetchone()
            return dict(new_row)

    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """ID'ye göre ürün getirir."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_product_price(self, product_id: int, new_price: float):
        """Ürün fiyatını günceller ve geçmişe yazar."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                UPDATE products 
                SET current_price = ?, last_checked_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_price, product_id))

            await conn.execute("""
                INSERT INTO price_history (product_id, price)
                VALUES (?, ?)
            """, (product_id, new_price))

            await conn.commit()

    async def add_tracking(
        self,
        user_id: int,
        product_id: int,
        target_price: Optional[float] = None,
        notify_on_any_drop: bool = True
    ):
        """Kullanıcı için ürün takibi başlatır veya günceller."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO trackings (user_id, product_id, target_price, notify_on_any_drop)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, product_id) DO UPDATE SET
                    target_price = excluded.target_price,
                    notify_on_any_drop = excluded.notify_on_any_drop;
            """, (user_id, product_id, target_price, 1 if notify_on_any_drop else 0))
            await conn.commit()

    async def remove_tracking(self, user_id: int, product_id: int) -> bool:
        """Kullanıcının ürün takibini siler."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                DELETE FROM trackings WHERE user_id = ? AND product_id = ?
            """, (user_id, product_id))
            await conn.commit()
            return cursor.rowcount > 0

    async def get_user_trackings(self, user_id: int) -> List[Dict[str, Any]]:
        """Kullanıcının takip ettiği tüm ürünleri listeler."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT 
                    p.id, p.url, p.platform, p.title, p.image_url, 
                    p.current_price, p.currency, p.last_checked_at,
                    t.target_price, t.notify_on_any_drop, t.created_at as tracked_since
                FROM trackings t
                JOIN products p ON t.product_id = p.id
                WHERE t.user_id = ?
                ORDER BY t.created_at DESC
            """, (user_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_active_products(self) -> List[Dict[str, Any]]:
        """En az bir kullanıcı tarafından takip edilen tüm ürünleri getirir."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT DISTINCT p.*
                FROM products p
                JOIN trackings t ON p.id = t.product_id
            """)
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_product_subscribers(self, product_id: int) -> List[Dict[str, Any]]:
        """Bir ürünü takip eden kullanıcıları ve tercihlerini getirir."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT t.user_id, t.target_price, t.notify_on_any_drop, u.first_name, u.username
                FROM trackings t
                JOIN users u ON t.user_id = u.telegram_id
                WHERE t.product_id = ?
            """, (product_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_price_history(self, product_id: int) -> List[Dict[str, Any]]:
        """Bir ürünün tüm fiyat geçmişini tarih sırasıyla getirir."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT price, recorded_at
                FROM price_history
                WHERE product_id = ?
                ORDER BY recorded_at ASC
            """, (product_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def save_custom_rule(
        self,
        domain: str,
        price_selector: str,
        title_selector: Optional[str] = None,
        image_selector: Optional[str] = None
    ):
        """Özel bir domain için CSS seçicilerini kaydeder."""
        domain = domain.lower().replace("http://", "").replace("https://", "").split("/")[0]
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO custom_site_rules (domain, price_selector, title_selector, image_selector)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    price_selector = excluded.price_selector,
                    title_selector = excluded.title_selector,
                    image_selector = excluded.image_selector;
            """, (domain, price_selector, title_selector, image_selector))
            await conn.commit()

    async def get_custom_rule(self, domain: str) -> Optional[Dict[str, Any]]:
        """Bir domaine ait özel seçici kuralını getirir."""
        domain = domain.lower().replace("http://", "").replace("https://", "").split("/")[0]
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM custom_site_rules WHERE domain = ?
            """, (domain,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_custom_rules(self) -> List[Dict[str, Any]]:
        """Tüm özel site kurallarını listeler."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM custom_site_rules ORDER BY domain ASC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

db = Database()
