@echo off
chcp 65001 >nul
echo Fixing ComSpec environment variable...
setx ComSpec "C:\Windows\System32\cmd.exe" /M
echo.
echo Done! Please restart VSCode or Kiro IDE for changes to take effect.
echo.
pause
