#!/usr/bin/env bash
# Запуск бота в фоновом режиме на macOS / Linux

# Переход в директорию скрипта
cd "$(dirname "$0")"

# Активация виртуального окружения, если оно есть
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Проверка, не запущен ли уже бот
if pgrep -f "python.*bot.py" > /dev/null; then
    echo "⚠️ Бот уже запущен!"
    exit 1
fi

nohup python3 bot.py > bot.log 2>&1 &
PID=$!
echo "✅ Telegram-бот запущен в фоновом режиме (PID: $PID)."
echo "📜 Логи вывода можно посмотреть в файле bot.log (команда: tail -f bot.log)"
