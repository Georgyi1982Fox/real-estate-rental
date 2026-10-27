@echo off
rem Bina.ai: скачать обновления из GitHub (ветка develop) и перезапустить (TASK-087).
chcp 65001 >nul
cd /d "%~dp0"

echo === Bina.ai: обновление ===
echo.
git checkout develop
if errorlevel 1 goto failed
git pull origin develop
if errorlevel 1 goto failed

rem Сайт Mini App теперь в Docker (TASK-123): старое окно «Bina - site» (npm run dev) занимает
rem порт 5173 — закрываем его, если открыто
taskkill /FI "WINDOWTITLE eq Bina - site*" /T /F >nul 2>&1

echo.
echo Пересобираю и перезапускаю сервисы и сайт (1-3 минуты)...
docker compose up -d --build
if errorlevel 1 goto failed

echo.
docker compose ps
echo.
echo Готово. Сайт Mini App работает внутри Docker — отдельное окно сайта больше не нужно.
pause
exit /b 0

:failed
echo.
echo Ошибка. Пришлите текст выше.
pause
exit /b 1
