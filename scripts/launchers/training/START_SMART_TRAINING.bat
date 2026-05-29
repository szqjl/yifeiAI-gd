@echo off
call "%~dp0..\_env.bat"
REM 智能训练工具快速启动脚本
REM 提供三种训练方式的快速入口

echo ========================================
echo   智能训练工具 - 快速启动
echo ========================================
echo.
echo 请选择训练方式:
echo.
echo 1. 标准训练 + Wandb 监控
echo 2. Optuna 超参数优化
echo 3. PyTorch Lightning 训练
echo 4. 查看使用文档
echo 5. 退出
echo.
set /p choice=请输入选项 (1-5): 

if "%choice%"=="1" goto train_wandb
if "%choice%"=="2" goto optuna
if "%choice%"=="3" goto lightning
if "%choice%"=="4" goto docs
if "%choice%"=="5" goto end

:train_wandb
echo.
echo ========================================
echo   启动标准训练 + Wandb 监控
echo ========================================
echo.
echo 提示: 首次使用需要运行 'wandb login' 登录
echo.
python src/train/stage7_optimized_training.py
goto end

:optuna
echo.
echo ========================================
echo   Optuna 超参数优化
echo ========================================
echo.
set /p n_trials=请输入试验次数 (默认50): 
if "%n_trials%"=="" set n_trials=50
echo.
echo 开始优化，试验次数: %n_trials%
echo 提示: 优化过程可能需要较长时间，请耐心等待
echo.
python src/train/optuna_hyperparameter_optimization.py --n_trials %n_trials%
goto end

:lightning
echo.
echo ========================================
echo   PyTorch Lightning 训练
echo ========================================
echo.
echo 提示: 首次使用需要运行 'wandb login' 登录
echo.
python src/train/stage7_lightning_training.py --use_wandb
goto end

:docs
echo.
echo ========================================
echo   打开使用文档
echo ========================================
echo.
start docs/training/智能训练插件使用指南.md
goto end

:end
echo.
echo 程序已退出
pause
