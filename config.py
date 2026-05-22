import os
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")
SOCKS_PROXY_URL = os.environ.get("SOCKS_PROXY_URL", "socks5://127.0.0.1:1080")

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GLOBAL_RATE_LIMIT_SECONDS = int(os.environ.get("GLOBAL_RATE_LIMIT_SECONDS", "60"))
HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "60.0"))

DOMAIN = os.environ.get("DOMAIN", "localhost")
YANDEX_VERIFICATION_CODE = os.environ.get("YANDEX_VERIFICATION_CODE", "")
