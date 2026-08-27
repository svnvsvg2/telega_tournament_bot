# Руководство по кросс-платформенной разработке (Windows & macOS)

Данное руководство позволит вам комфортно вести разработку проекта **Telegram_Bot_MK** как на **Windows**, так и на **macOS**, используя единый Git-репозиторий без конфликтов окончаний строк (`CRLF`/`LF`), базы данных и виртуальных окружений.

---

## 1. Концепция синхронизации между компьютерами

При работе на двух операционных системах соблюдается чёткое разделение файлов:

### 🟢 Синхронизируется через Git:
- Исходный код Python (`bot.py`, `server.py`, `database.py`, `config.py`)
- Файлы веба (`web/*`)
- Шаблоны настроек и правил (`.env.example`, `rules.txt`, `reglament.md`)
- Конфигурации Git и зависимостей (`requirements.txt`, `.gitignore`, `.gitattributes`)
- Скрипты запуска для обоих ОС (`start_bot.vbs`, `stop_bot.bat`, `start_bot.sh`, `stop_bot.sh`)

### 🔴 НЕ синхронизируется (остаётся на каждом устройстве локально):
- `.env` — ваши токены бота, пароли админов (могут быть разными для тестов на Mac и PC)
- `participants.db` — база данных SQLite (чтобы Git не ломал бинарные конфликты)
- `venv/` / `.venv/` — виртуальные окружения Python (для каждой ОС они свои!)
- Временные логи и кэши (`bot.log`, `__pycache__`, `.DS_Store`, `Thumbs.db`)

---

## 2. Настройка Git для предотвращения конфликтов (CRLF / LF)

Windows по умолчанию использует перенос строки `CRLF`, а macOS — `LF`.

В проекте уже настроен файл `.gitattributes`, который автоматически нормализует текстовые файлы к `LF` при отправке в Git.

Для идеальной работы выполните в терминале на каждом компьютере единоразовую настройку:

### На Windows:
```bash
git config --global core.autocrlf true
```

### На macOS:
```bash
git config --global core.autocrlf input
```

---

## 3. Первичная развёртка проекта

### 🪟 Инструкция для Windows:

1. **Клонирование репозитория:**
   ```powershell
   git clone <ссылка_на_ваш_репозиторий>
   cd Telegram_Bot_MK
   ```

2. **Создание и активация виртуального окружения:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   *(Если PowerShell выдаёт ошибку выполнения скриптов, выполните `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)*

3. **Установка зависимостей:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Создание конфигурационного файла:**
   ```powershell
   copy .env.example .env
   ```
   *Заполните `.env` вашим `BOT_TOKEN` и настройками.*

---

### 🍎 Инструкция для macOS:

1. **Клонирование репозитория:**
   ```bash
   git clone <ссылка_на_ваш_репозиторий>
   cd Telegram_Bot_MK
   ```

2. **Выдача прав на выполнение скриптов:**
   ```bash
   chmod +x *.sh
   ```

3. **Создание и активация виртуального окружения:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Установка зависимостей:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Создание конфигурационного файла:**
   ```bash
   cp .env.example .env
   ```
   *Заполните `.env` вашим `BOT_TOKEN` и настройками.*

---

## 4. Запуск и остановка бота

### 🪟 На Windows:

- **Интерактивный режим (видеть логи в терминале):**
  ```powershell
  python bot.py
  ```
- **Фоновый запуск (без открытого окна консоли):**
  Дважды кликните по файлу `start_bot.vbs`
- **Остановка фонового бота:**
  Запустите файл `stop_bot.bat`

---

### 🍎 На macOS:

- **Интерактивный режим (видеть логи в терминале):**
  ```bash
  python3 bot.py
  ```
- **Фоновый запуск (работает в фоновом режиме `nohup`):**
  ```bash
  ./start_bot.sh
  ```
  *Логи вывода автоматически пишутся в файл `bot.log`. Просмотр логов: `tail -f bot.log`*
- **Остановка фонового бота:**
  ```bash
  ./stop_bot.sh
  ```

---

## 5. Ежедневный рабочий процесс (Workflow)

Когда вы переходите с одного компьютера на другой:

1. **Перед уходом с одного компьютера:**
   ```bash
   git add .
   git commit -m "Описание внесенных изменений"
   git push origin main
   ```

2. **При приходе на другой компьютер:**
   ```bash
   git pull origin main
   ```

3. Если вы добавляли новые библиотеки в `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

---

## 6. Что делать с базой данных `participants.db`?

Так как `participants.db` находится в `.gitignore`, тестовые участники не перезаписывают друг друга при переключении между ПК.

- Если вам нужно скопировать текущую тестовую базу с Windows на Mac (или наоборот), просто перешлите файл `participants.db` вручную (через Telegram/AirDrop/флешку) в корень папки проекта.
- Чтобы сбросить базу данных для тестов, используйте админ-команду в Telegram: `/reset confirm` или удалите файл `participants.db` (он автоматически пересоздастся при запуске).

---

## 7. Чек-лист решения частых проблем

| Проблема | Причина | Решение |
| :--- | :--- | :--- |
| **`Permission denied` при запуске `.sh` на Mac** | У файла нет прав на исполнение | Выполните `chmod +x start_bot.sh stop_bot.sh` |
| **`cannot be loaded because running scripts is disabled` на Windows** | Политика безопасности PowerShell | Выполните `Set-ExecutionPolicy RemoteSigned -Scope Process` |
| **Конфликты `^M` / переносов строк в Git** | Разница CRLF (Win) / LF (Mac) | `.gitattributes` исправляет это. Выполните `git checkout -- .` |
| **`ModuleNotFoundError: No module named ...`** | Не активировано `venv` или не установлены пакеты | Активируйте окружение (`source venv/bin/activate` / `.\venv\Scripts\Activate.ps1`) и запустите `pip install -r requirements.txt` |
