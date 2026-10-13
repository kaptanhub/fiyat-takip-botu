FROM python:3.11-slim

# Gerekli sistem paketleri ve Türkiye saat dilimi ayarı
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Istanbul
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodları kopyala
COPY . .

# Botu başlat
CMD ["python", "main.py"]
