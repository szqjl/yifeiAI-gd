@echo off
chcp 65001 >nul 2>&1
title Strategy Tasks Training - 6 Strategy Tasks
color 0A

echo.
echo ================================================================
echo            Strategy Tasks Training - 6 Strategy Tasks
echo ================================================================
echo.

echo [Training Tasks]
echo 1. Card Grouping Strategy Classification (7 classes)
echo 2. Role Judgment (Attacker/Assistant/Balanced)
echo 3. Hand Power Estimation (0-10 points)
echo 4. Protect/Suppress Judgment
echo 5. Bomb Playing Timing
echo 6. Red Heart Strategy
echo.

echo [Training Configuration]
echo - Data Size: 10000 samples
echo - Epochs: 50
echo - Batch Size: 64
echo - Learning Rate: 0.0003
echo - Strategy Tasks Weight: 0.5
echo - Strategy Consistency Loss Weight: 0.2-0.5
echo - Joint Loss Weight: 0.3
echo.

echo [Monitoring]
echo - Real-time loss and accuracy display during training
echo - Checkpoint saved every 10 epochs
echo - Training logs saved in training_logs/ directory
echo - Model saved to models/bc_model_strategy_tasks.pth
echo.

echo [Improvements]
echo - Strategy Consistency Loss: Encourages action and strategy consistency
echo - Joint Loss: Directly encourages both action and strategy to be correct
echo - Improved Strategy Understanding Rate: Uses 90%% match rate (not 100%%)
echo.

echo Starting training...
echo.

cd /d "%~dp0"
python scripts/training/train_strategy_tasks.py

echo.
echo ================================================================
echo Training completed or interrupted
echo ================================================================
pause

