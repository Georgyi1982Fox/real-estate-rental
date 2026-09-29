@echo off
rem Bina.ai: восстановить базу из копии (TASK-045).
rem Перед заменой текущая база сохраняется в backups\before-restore-....dump
chcp 65001 >nul
cd /d "%~dp0"

echo === Восстановление базы Bina.ai ===
echo.
docker compose exec backup sh /backup.sh list
if errorlevel 1 (
    echo Сервис backup не запущен. Сначала start-bina.bat
    pause
    exit /b 1
)
echo.
echo Enter — последняя копия. Или введите имя файла, например bina-2026-09-29_03-00.dump
set "FILE=latest"
set /p "FILE=Копия: "
echo.
echo ВНИМАНИЕ: всё, что сейчас в базе, заменится данными из копии "%FILE%".
set "OK="
set /p "OK=Продолжить? Введите yes: "
if /i not "%OK%"=="yes" (
    echo Отменено.
    pause
    exit /b 0
)

echo.
echo Останавливаю бота, API и парсер...
docker compose stop api bot scraper
docker compose exec backup sh /backup.sh restore "%FILE%"
set "RESULT=%errorlevel%"
echo.
echo Запускаю обратно...
docker compose start api bot scraper
echo.
if "%RESULT%"=="0" (
    echo Готово: база восстановлена.
) else (
    echo Ошибка: база НЕ изменена. Пришлите текст выше.
)
pause
