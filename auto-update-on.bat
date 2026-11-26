@echo off
rem Bina.ai: включить автообновление (TASK-125). Раз в 10 минут, пока компьютер включён
rem и вы вошли в Windows, проверяет GitHub; есть новое — обновляет само (auto-update-bina.ps1).
chcp 65001 >nul
cd /d "%~dp0"

rem conhost --headless — без мелькающего окна каждые 10 минут
schtasks /Create /F /SC MINUTE /MO 10 /TN "Bina auto-update" /TR "conhost.exe --headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"%~dp0auto-update-bina.ps1\""
if errorlevel 1 goto failed

rem Первая проверка — сразу
schtasks /Run /TN "Bina auto-update" >nul

echo.
echo Автообновление включено: раз в 10 минут.
echo Журнал: auto-update.log в этой папке. Выключить: auto-update-off.bat
pause
exit /b 0

:failed
echo.
echo Не получилось. Пришлите текст выше.
pause
exit /b 1
