@echo off
echo Остановка Telegram-бота...
powershell -Command "Get-CimInstance Win32_Process -Filter \"name = 'python.exe' or name = 'pythonw.exe'\" | Where-Object { $_.CommandLine -like '*bot.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Бот остановлен.
pause
