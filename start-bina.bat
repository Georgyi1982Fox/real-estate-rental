@echo off
rem Bina.ai: запуск всего одним двойным кликом (TASK-087).
rem Docker (база, API, бот, парсер) + туннель Cloudflare + сайт Mini App.
chcp 65001 >nul
cd /d "%~dp0"

echo === Bina.ai: запуск ===
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop не запущен, запускаю...
    if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
        start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo Не нашёл Docker Desktop. Запустите его вручную и снова откройте этот файл.
        pause
        exit /b 1
    )
)

echo Жду, пока Docker будет готов...
set /a tries=0
:wait_docker
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready
set /a tries+=1
if %tries% GEQ 60 (
    echo Docker не запустился за 5 минут. Проверьте Docker Desktop и попробуйте ещё раз.
    pause
    exit /b 1
)
timeout /t 5 /nobreak >nul
goto wait_docker

:docker_ready
echo.
echo 1/3 База, API, бот и парсер...
docker compose up -d
if errorlevel 1 (
    echo Ошибка docker compose. Пришлите текст выше.
    pause
    exit /b 1
)

echo.
echo 2/3 Туннель https://bina.test-realtybot.ru (отдельное окно, не закрывайте)
start "Bina - tunnel" /d "%~dp0" cmd /k cloudflared tunnel run realtybot-dev

echo 3/3 Сайт Mini App (отдельное окно, не закрывайте)
start "Bina - site" /d "%~dp0frontend" cmd /k npm run dev -- --host 127.0.0.1

echo.
docker compose ps
echo.
echo Готово. Через минуту откройте бота в Telegram или https://bina.test-realtybot.ru
echo Остановить всё: stop-bina.bat
pause
