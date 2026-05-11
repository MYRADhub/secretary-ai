#!/bin/bash
set -e

echo "=== Secretary AI — Server Setup ==="

# system deps
apt-get update -qq
apt-get install -y python3.12 python3.12-venv python3-pip git postgresql-client

# create app user
if ! id -u secretary &>/dev/null; then
    useradd -m -s /bin/bash secretary
fi

# clone or pull repo
APP_DIR="/home/secretary/secretary-ai"
if [ -d "$APP_DIR" ]; then
    echo "Repo exists, pulling latest..."
    sudo -u secretary git -C "$APP_DIR" pull
else
    echo "Cloning repo..."
    sudo -u secretary git clone https://github.com/MYRADhub/secretary-ai.git "$APP_DIR"
fi

# install python deps
sudo -u secretary python3.12 -m venv "$APP_DIR/.venv"
sudo -u secretary "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# copy env file if not present
if [ ! -f "$APP_DIR/.env" ]; then
    echo "WARNING: No .env file found at $APP_DIR/.env"
    echo "Copy your .env file there before starting the service."
fi

# install systemd service
cp /home/secretary/secretary-ai/deploy/secretary-ai.service /etc/systemd/system/secretary-ai.service
systemctl daemon-reload
systemctl enable secretary-ai
systemctl restart secretary-ai

echo ""
echo "=== Done ==="
echo "Check status with: systemctl status secretary-ai"
echo "View logs with:    journalctl -u secretary-ai -f"
