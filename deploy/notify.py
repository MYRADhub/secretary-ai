import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv("/home/secretary/secretary-ai/.env")

token = os.getenv("TELEGRAM_BOT_TOKEN")
user_id = os.getenv("TELEGRAM_ALLOWED_USER_ID")
message = sys.argv[1] if len(sys.argv) > 1 else "Update deployed."

if not token or not user_id:
    print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_ALLOWED_USER_ID")
    sys.exit(1)

response = httpx.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": user_id, "text": message},
)
print(response.json())
