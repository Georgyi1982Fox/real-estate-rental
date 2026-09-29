@echo off
rem Bina.ai: копия базы прямо сейчас в папку backups (TASK-044).
chcp 65001 >nul
cd /d "%~dp0"
docker compose exec backup sh /backup.sh once
if errorlevel 1 (
    echo Ошибка. Запущен ли Bina? Сначала start-bina.bat
    pause
    exit /b 1
)
echo.
docker compose exec backup sh /backup.sh list
echo.
echo Копии лежат в папке backups рядом с этим файлом.
pause
