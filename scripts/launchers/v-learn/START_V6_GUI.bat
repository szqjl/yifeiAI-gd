@echo off
call "%~dp0..\_env.bat"
chcp 65001 >nul
REM Start V6 Batch Test GUI
REM Stage 6 Game-Oriented Training System

echo ========================================
echo Guandan AI Batch Battle System - V6
echo ========================================
echo.
echo Config: YiFei V6 vs lalala First Prize AI
echo Team A: yf1_v6 (Position 0) + yf2_v6 (Position 2)
echo Team B: lalala client3 (Position 1) + client4 (Position 3)
echo.
echo V6 Core Features (Stage 6 Game-Oriented Training):
echo   - Strategy Reason Learning: Understand WHY to choose
echo   - Win Rate Oriented Loss: Learn WHAT works
echo   - Dynamic Threshold Adjustment: Adaptive to situation
echo   - Probability Calibration: Improve prediction accuracy
echo   - Comprehensive Evaluation: Multi-dimensional validation
echo.
echo Stage 6 Core Philosophy:
echo   From "Card Prediction AI" to "Game Winning AI"
echo   From "Technical Advancement" to "Game Effectiveness"
echo   From "Data Fitting" to "Strategy Learning"
echo.
echo Expected Improvements (vs V5):
echo   - Game Win Rate: 0%% -^> 40-60%%
echo   - Strategy Understanding: 1.22%% -^> 30-40%%
echo   - Prediction Accuracy: 40.4%% -^> 60-70%%
echo   - Over-Prediction Rate: 59.6%% -^> 20-30%%
echo.
echo Starting GUI...
echo ========================================
echo.

py scripts/gui/batch_executor_gui.py

pause

