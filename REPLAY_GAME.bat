@echo off
REM Simple batch file - no Chinese characters to avoid encoding issues
cd /d "%~dp0"
python replay.py
pause
