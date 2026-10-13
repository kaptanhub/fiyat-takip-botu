#!/bin/bash
# Ubuntu / Debian VPS için otomatik servis kurulum betiği

set -e

echo "=== Fiyat Takip Botu VPS Kurulumu Başlatılıyor ==="

# Sistem güncelleme ve Python yükleme
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# Sanal ortam oluşturma
if [ ! -d "venv" ]; then
    echo "Python sanal ortamı (venv) oluşturuluyor..."
    python3 -m venv venv
fi

# Bağımlılıkları yükleme
echo "Bağımlılıklar yükleniyor..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

# systemd servis dosyası oluşturma
SERVICE_FILE="/etc/systemd/system/fiyat-takip-bot.service"

echo "Systemd servisi oluşturuluyor: $SERVICE_FILE"

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Telegram E-Ticaret Fiyat Takip Botu
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=$CURRENT_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

# Servisi etkinleştirme ve başlatma
sudo systemctl daemon-reload
sudo systemctl enable fiyat-takip-bot
sudo systemctl restart fiyat-takip-bot

echo "=== Kurulum Başarıyla Tamamlandı! ==="
echo "Servis durumunu kontrol etmek için: sudo systemctl status fiyat-takip-bot"
echo "Logları canlı izlemek için: sudo journalctl -u fiyat-takip-bot -f"
