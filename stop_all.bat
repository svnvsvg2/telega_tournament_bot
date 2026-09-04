@echo off
chcp 65001 > nul
echo Остановка всех процессов турнира (Бот и Веб-сервер)...
powershell -Command "Get-CimInstance Win32_Process -Filter \"name = 'python.exe' or name = 'pythonw.exe'\" | Where-Object { $_.CommandLine -like '*bot.py*' -or $_.CommandLine -like '*server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Все серверные процессы успешно остановлены.
pause
