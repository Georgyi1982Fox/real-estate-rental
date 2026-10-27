@echo off
rem Bina.ai: остановить сервисы Docker (данные базы сохраняются) (TASK-087).
chcp 65001 >nul
cd /d "%~dp0"
docker compose stop
echo.
echo Сервисы и сайт остановлены. Окно туннеля закройте вручную.
pause
