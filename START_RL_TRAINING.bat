@echo off
echo Starting Guandan AI Self-Play Training...
echo This will train the AI by playing against itself.
echo Press Ctrl+C to stop.
echo.

:loop
py src/train/self_play.py
if errorlevel 1 goto error
goto loop

:error
echo.
echo Training script encountered an error.
pause
