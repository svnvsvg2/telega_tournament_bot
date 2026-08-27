#!/usr/bin/env bash
# Остановка бота на macOS / Linux

echo "🛑 Остановка Telegram-бота..."

PIDS=$(pgrep -f "python.*bot.py")

if [ -z "$PIDS" ]; then
    echo "ℹ️ Запущенных процессов бота не найдено."
else
    pkill -f "python.*bot.py"
    echo "✅ Бот успешно остановлен (PID: $PIDS)."
fi
