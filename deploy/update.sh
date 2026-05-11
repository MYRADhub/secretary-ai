#!/bin/bash
set -e

APP_DIR="/home/secretary/secretary-ai"

echo "Pulling latest code..."
sudo -u secretary git -C "$APP_DIR" pull

echo "Installing any new dependencies..."
sudo -u secretary "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "Restarting service..."
systemctl restart secretary-ai

echo "Done. Status:"
systemctl status secretary-ai --no-pager

echo "Sending deploy notification..."
/home/secretary/secretary-ai/.venv/bin/python /home/secretary/secretary-ai/deploy/notify.py "Update deployed."
