#!/bin/bash
set -e

APP_DIR="/home/murad/secretary-ai"

echo "Pulling latest code..."
git -C "$APP_DIR" pull

echo "Installing any new dependencies..."
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "Restarting service..."
sudo -n /bin/systemctl restart secretary-ai

echo "Done."
sleep 5
echo "Sending deploy notification..."
"$APP_DIR/.venv/bin/python" "$APP_DIR/deploy/notify.py" "Update deployed."
