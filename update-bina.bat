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

echo.
echo Пересобираю и перезапускаю сервисы (1-3 минуты)...
docker compose up -d --build
if errorlevel 1 goto failed

echo.
echo Обновляю пакеты сайта...
cd frontend
call npm install --no-audit --no-fund
cd ..

echo.
docker compose ps
echo.
echo Готово. Если окно сайта было открыто — закройте его и запустите start-bina.bat.
pause
exit /b 0

:failed
echo.
echo Ошибка. Пришлите текст выше.
pause
exit /b 1
