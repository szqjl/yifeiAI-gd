@echo off
call "%~dp0..\_env.bat"
REM ========================================
REM 阶段6游戏导向训练GUI工具启动脚本（增强版）
REM 整合1312数据转换器，包含完整的数据加载、转换、训练、监控、评估功能
REM 直接双击运行即可启动图形化界面
REM ========================================

echo ========================================
echo [STAGE6] 阶段6游戏导向训练GUI工具（增强版）
echo ========================================
echo.
echo 核心功能：
echo   - 数据加载和格式转换（自动检测1312格式）
echo   - 数据统计分析和质量检查
echo   - 训练配置保存/加载
echo   - 实时训练进度监控
echo   - 多维度模型评估
echo   - 训练报告生成
echo.

REM 设置控制台编码为UTF-8
chcp 65001 >nul 2>&1

REM ========================================
REM 启动前检查
REM ========================================
echo [CHECK] 正在检查环境...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python未安装或不在PATH中！
    echo.
    echo 请先安装Python 3.7或更高版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM 显示Python版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python版本: %PYTHON_VERSION%

REM 检查必要的Python包
echo [CHECK] 检查必要的Python包...
python -c "import torch" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] PyTorch未安装，正在安装...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
)

python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] tkinter未安装！
    echo 请安装Python时选择"Install tkinter"
    pause
    exit /b 1
)

python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] numpy未安装，正在安装...
    pip install numpy
)

echo [OK] 所有必要的包已安装
echo.

REM ========================================
REM 检查数据目录
REM ========================================
if not exist "game_records" (
    echo [INFO] 创建game_records目录...
    mkdir game_records
    echo [OK] game_records目录已创建
    echo.
)

REM ========================================
REM 检查模型目录
REM ========================================
if not exist "models" (
    echo [INFO] 创建models目录...
    mkdir models
    echo [OK] models目录已创建
    echo.
)

REM ========================================
REM 启动GUI
REM ========================================
echo ========================================
echo [START] 正在启动阶段6训练GUI（增强版）...
echo ========================================
echo.
echo 提示：
echo   - GUI启动后，请先检查"数据管理"标签页
echo   - 点击"检查并转换1312格式"自动转换数据
echo   - 在"训练配置"标签页配置训练参数
echo   - 点击"开始训练"开始训练
echo   - 在"训练监控"标签页查看训练进度
echo   - 在"训练评估"标签页评估模型效果
echo.
echo ========================================
echo.

REM 运行Python GUI脚本
python scripts/training/run_stage6_training_gui.py

REM 如果Python命令失败，显示错误信息
if errorlevel 1 (
    echo.
    echo ========================================
    echo [ERROR] GUI启动失败！
    echo ========================================
    echo.
    echo 可能的原因：
    echo 1. Python版本过低（需要3.7+）
    echo 2. 缺少必要的Python包
    echo 3. GUI脚本文件损坏
    echo 4. 1312转换器模块导入失败
    echo.
    echo 解决方案：
    echo 1. 确保Python 3.7+已安装
    echo 2. 运行以下命令安装依赖：
    echo    pip install torch torchvision numpy
    echo 3. 检查脚本文件是否存在：
    echo    - run_stage6_training_gui.py
    echo    - stage6_training_gui_enhanced.py
    echo    - src/knowledge_processor/1312_replay_converter.py
    echo 4. 如果1312转换器导入失败，可以继续使用（功能会受限）
    echo.
    echo 详细错误信息请查看上方的Python输出
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo [END] GUI已关闭
echo ========================================
echo.
echo 提示：
echo   - 训练配置已自动保存
echo   - 模型文件保存在models目录
echo   - 训练日志可在GUI中查看
echo.
pause
