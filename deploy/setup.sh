#!/bin/bash
set -e

echo "=== Secretary AI — Server Setup (home server) ==="

APP_DIR="/home/murad/secretary-ai"

# system deps
sudo apt-get update -qq
sudo apt-get install -y python3.12 python3.12-venv python3-pip git postgresql-16 postgresql-client-16

# clone or pull repo
if [ -d "$APP_DIR" ]; then
    echo "Repo exists, pulling latest..."
    git -C "$APP_DIR" pull
else
    echo "Cloning repo..."
    git clone https://github.com/MYRADhub/secretary-ai.git "$APP_DIR"
fi

# install python deps
python3.12 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# env file check
if [ ! -f "$APP_DIR/.env" ]; then
    echo "WARNING: No .env file found at $APP_DIR/.env"
    echo "Copy your .env file there before starting the service."
fi

# install systemd service
sudo cp "$APP_DIR/deploy/secretary-ai.service" /etc/systemd/system/secretary-ai.service
sudo systemctl daemon-reload
sudo systemctl enable secretary-ai
sudo systemctl restart secretary-ai

echo ""
echo "=== Done ==="
echo "Check status with: sudo systemctl status secretary-ai"
echo "View logs with:    journalctl -u secretary-ai -f"
