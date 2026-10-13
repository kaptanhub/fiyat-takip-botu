import io
from typing import List, Dict, Any
from datetime import datetime
import matplotlib
matplotlib.use("Agg")  # GUI gerektirmeyen arka plan
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def generate_price_chart(product_title: str, history: List[Dict[str, Any]], currency: str = "TL") -> io.BytesIO:
    """
    Ürünün fiyat geçmişini şık bir çizgi grafiği haline getirir ve bellek içi PNG tamponu döndürür.
    """
    dates = []
    prices = []

    for item in history:
        raw_date = item["recorded_at"]
        price = float(item["price"])
        try:
            # SQLite formatı: 'YYYY-MM-DD HH:MM:SS'
            dt = datetime.strptime(raw_date.split(".")[0], "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt = datetime.now()
        dates.append(dt)
        prices.append(price)

    # Grafik ayarları
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=130)

    # Arka plan ve renkler
    fig.patch.set_facecolor("#f8f9fa")
    ax.set_facecolor("#ffffff")

    # Çizgi çizimi
    ax.plot(dates, prices, color="#0088cc", linewidth=2.5, marker="o", markersize=6, label="Fiyat")

    # Minimum ve maksimum fiyatları vurgula
    min_price = min(prices)
    max_price = max(prices)
    min_idx = prices.index(min_price)
    ax.plot(dates[min_idx], min_price, marker="*", markersize=14, color="#28a745", label=f"En Düşük: {min_price:,.2f} {currency}")

    # Eksen etiketleri ve formatlama
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
    fig.autofmt_xdate(rotation=30)

    # Başlık (uzunsa kırp)
    short_title = (product_title[:45] + "...") if len(product_title) > 48 else product_title
    ax.set_title(f"Fiyat Geçmişi: {short_title}", fontsize=12, fontweight="bold", pad=12, color="#212529")
    ax.set_ylabel(f"Fiyat ({currency})", fontsize=10, color="#495057")

    # Grid ve sınırlar
    ax.grid(True, linestyle="--", alpha=0.6, color="#ced4da")
    ax.legend(loc="best", framealpha=0.9)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
