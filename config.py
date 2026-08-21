# ============================================================
#  config.py — Barcha sozlamalar bir joyda
# ============================================================
import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# --- Foydalanuvchi ruxsati (whitelist) ---
_raw_ids = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: list[int] = [
    int(uid.strip()) for uid in _raw_ids.split(",") if uid.strip()
]

# --- AI API Keys ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str   = os.getenv("GROQ_API_KEY", "")

# --- AI Model sozlamalari ---
GEMINI_MODEL   = "gemini-3.6-flash"
GROQ_MODEL     = "openai/gpt-oss-120b"  # Fallback model

# --- Xotira / Encryption ---
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

# --- Database ---
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot_data.db")

# --- GitHub (qidiruv uchun) ---
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

# --- Context Window sozlamalari ---
MAX_RECENT_MESSAGES  = 10   # LLM ga yuboriladigan oxirgi xabarlar soni
MAX_SUMMARY_TOKENS   = 500  # Xulosa maksimal uzunligi (token)

# --- Scheduler ---
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")

# --- Fayl cheklovlari ---
MAX_FILE_SIZE_MB    = 20    # Maksimal fayl hajmi (MB)
ALLOWED_EXTENSIONS  = {
    "documents": [".pdf", ".txt", ".docx", ".md"],
    "images":    [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    "audio":     [".ogg", ".mp3", ".wav", ".m4a"],
}

# --- Logging ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# --- Rate Limiting ---
RATE_LIMIT_MESSAGES = 30   # 1 daqiqada maksimal xabarlar soni
RATE_LIMIT_WINDOW   = 60   # Sekund

def validate_config() -> None:
    """Muhim konfiguratsiyalarni tekshirish."""
    errors = []
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN sozlanmagan!")
    if not GEMINI_API_KEY and not GROQ_API_KEY:
        errors.append("GEMINI_API_KEY yoki GROQ_API_KEY dan kamida biri kerak!")
    if not ENCRYPTION_KEY:
        errors.append("ENCRYPTION_KEY sozlanmagan! Memory xavfsizligi uchun kerak.")
    if errors:
        raise ValueError("Config xatolari:\n" + "\n".join(f"  - {e}" for e in errors))
