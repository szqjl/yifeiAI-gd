@echo off
chcp 65001 >nul
echo ========================================
echo   yife-gd-bot - Lark Bot Event Consumer
echo   Profile: yife-gd-bot
echo ========================================
echo.
echo Starting event consumer...
echo Press Ctrl+C to stop
echo.
lark-cli event consume im.message.receive_v1 --profile yife-gd-bot --as bot
pause
