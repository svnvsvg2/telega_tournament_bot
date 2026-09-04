"""
Настройки бота. Все значения задаются в файле .env (см. .env.example)
и в rules.txt (текст правил турнира).
"""
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ID администраторов бота через запятую, напр. "111111111,222222222"
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

ORGANIZER_USERNAME = os.getenv("ORGANIZER_USERNAME", "").replace("@", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "comp_games_lovers_bot").replace("@", "").strip()
BOT_URL = f"https://t.me/{BOT_USERNAME}"

ORGANIZATION_NAME = os.getenv("ORGANIZATION_NAME", "DARACYBER")
TOURNAMENT_NAME = os.getenv("TOURNAMENT_NAME", "DARACYBER Mortal Kombat 1 Championship")


# Формат: 2026-09-15 18:00
TOURNAMENT_DATETIME_STR = os.getenv("TOURNAMENT_DATETIME", "")
TOURNAMENT_DATETIME = (
    datetime.strptime(TOURNAMENT_DATETIME_STR, "%Y-%m-%d %H:%M")
    if TOURNAMENT_DATETIME_STR
    else None
)

# За сколько часов до турнира присылать напоминание с просьбой подтвердить участие
REMINDER_HOURS_BEFORE = int(os.getenv("REMINDER_HOURS_BEFORE", "24"))

# Через сколько часов после напоминания проверять, кто не подтвердился, и слать список админу
CONFIRMATION_CHECK_HOURS_AFTER = int(os.getenv("CONFIRMATION_CHECK_HOURS_AFTER", "12"))

MAX_PARTICIPANTS = int(os.getenv("MAX_PARTICIPANTS", "16"))

ADMIN_LOGIN = os.getenv("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "4321")
ADMIN_PIN = os.getenv("ADMIN_PIN", "4321")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "8088")))
WEB_URL = os.getenv("WEB_URL", f"http://localhost:{WEB_PORT}")



def load_rules() -> str:
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Правила турнира пока не опубликованы. Следите за объявлениями!"


RULES_TEXT = load_rules()
