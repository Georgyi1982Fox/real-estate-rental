@echo off
rem Bina.ai: выключить автообновление (TASK-125). Обновлять — вручную: update-bina.bat
chcp 65001 >nul
schtasks /Delete /F /TN "Bina auto-update"
echo.
echo Автообновление выключено.
pause
