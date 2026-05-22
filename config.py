import os
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")
SOCKS_PROXY_URL = os.environ.get("SOCKS_PROXY_URL", "socks5://127.0.0.1:1080")

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gemini-2.5-flash")
GLOBAL_RATE_LIMIT_SECONDS = int(os.environ.get("GLOBAL_RATE_LIMIT_SECONDS", "5"))
HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "60.0"))

DOMAIN = os.environ.get("DOMAIN", "localhost")
SITE_URL = os.environ.get("SITE_URL", f"https://{DOMAIN}")
YANDEX_VERIFICATION_CODE = os.environ.get("YANDEX_VERIFICATION_CODE", "")

DB_PATH = os.environ.get("DB_PATH", "/home/alex/ctf/ctf.db")
LEVELS_DIR = os.environ.get("LEVELS_DIR", "/home/alex/ctf/levels")

SESSION_SECRET = os.environ["SESSION_SECRET"]
SESSION_COOKIE = os.environ.get("SESSION_COOKIE", "ctf_sess")
SESSION_MAX_AGE_SECONDS = int(os.environ.get("SESSION_MAX_AGE_SECONDS", str(60 * 60 * 24 * 30)))

DAILY_QUOTA = int(os.environ.get("DAILY_QUOTA", "50"))
MAX_CONVERSATION_TURNS = int(os.environ.get("MAX_CONVERSATION_TURNS", "100"))

SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ["SMTP_PORT"])
SMTP_USERNAME = os.environ["SMTP_USERNAME"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USERNAME)
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "MIPT Prompts CTF")

EMAIL_TOKEN_TTL_HOURS = int(os.environ.get("EMAIL_TOKEN_TTL_HOURS", "24"))
