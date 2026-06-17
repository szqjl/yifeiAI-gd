@echo off
call "%~dp0..\_env.bat"
REM Stage 7 依赖包安装脚本

echo ========================================
echo Stage 7 依赖包安装
echo ========================================
echo.

REM 检查Python环境
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装或不在PATH中
    echo 请先安装Python 3.8+
    pause
    exit /b 1
)

echo [OK] Python环境检查通过
python --version

echo.
echo 正在检查已安装的包...

REM 检查torch
python -c "import torch; print(f'PyTorch版本: {torch.__version__}')" 2>nul
if errorlevel 1 (
    echo [需要安装] PyTorch
    set NEED_TORCH=1
) else (
    echo [OK] PyTorch已安装
)

REM 检查numpy
python -c "import numpy; print(f'NumPy版本: {numpy.__version__}')" 2>nul
if errorlevel 1 (
    echo [需要安装] NumPy
    set NEED_NUMPY=1
) else (
    echo [OK] NumPy已安装
)

REM 检查其他必要包
python -c "import json, pathlib, logging, time, datetime" 2>nul
if errorlevel 1 (
    echo [警告] 某些标准库可能不可用
) else (
    echo [OK] 标准库检查通过
)

echo.

REM 如果需要安装包
if defined NEED_TORCH (
    echo 正在安装PyTorch...
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    if errorlevel 1 (
        echo [错误] PyTorch安装失败
        echo 尝试使用conda安装: conda install pytorch cpuonly -c pytorch
        pause
        exit /b 1
    )
    echo [OK] PyTorch安装成功
)

if defined NEED_NUMPY (
    echo 正在安装NumPy...
    pip install numpy
    if errorlevel 1 (
        echo [错误] NumPy安装失败
        pause
        exit /b 1
    )
    echo [OK] NumPy安装成功
)

echo.
echo ========================================
echo 依赖包安装完成！
echo ========================================
echo.

REM 最终验证
echo 进行最终验证...
python -c "
import torch
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time
from datetime import datetime

print('✓ 所有依赖包验证成功')
print(f'✓ PyTorch版本: {torch.__version__}')
print(f'✓ NumPy版本: {np.__version__}')
print(f'✓ 设备支持: {torch.device(\"cpu\")}')
"

if errorlevel 1 (
    echo [错误] 依赖包验证失败
    pause
    exit /b 1
)

echo.
echo [OK] 所有依赖包已就绪，可以运行Stage 7训练！
echo.
echo 下一步:
echo   1. 运行 START_STAGE7_TRAINING.bat 开始训练
echo   2. 或者直接运行: cd src\train && python stage7_robust_training.py
echo.
pause