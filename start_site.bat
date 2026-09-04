@echo off
chcp 65001 > nul
title DARACYBER Tournament Web Server
echo ===================================================
echo   Запуск веб-сервера DARACYBER ESPORTS
echo   Адрес сайта: http://localhost:8088
echo   Админ-панель: http://localhost:8088/admin (пароль 4321)
echo ===================================================
echo Открытие сайта в браузере...
start "" "http://localhost:8088"
python server.py
pause
