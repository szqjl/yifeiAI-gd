@echo off
chcp 65001 >nul
REM ============================================================
REM 训练完成后自动评估脚本
REM 用于验证训练结果、评估模型效果、分析训练效果
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo 训练完成后评估工具
echo ============================================================
echo.

REM 检查模型文件是否存在
if not exist "models\bc_model_v1.pth" (
    echo [错误] 模型文件不存在: models\bc_model_v1.pth
    echo 请先完成训练。
    echo.
    pause
    exit /b 1
)

echo [信息] 找到模型文件: models\bc_model_v1.pth
echo.

REM 1. 验证训练结果
echo ============================================================
echo [1/3] 验证训练结果
echo ============================================================
python src/train/check_training_completion.py
if errorlevel 1 (
    echo [警告] 验证过程出现错误
)
echo.
pause

REM 2. 评估模型效果
echo ============================================================
echo [2/3] 评估模型效果
echo ============================================================
python src/train/evaluate_model.py
if errorlevel 1 (
    echo [警告] 评估过程出现错误
)
echo.
pause

REM 3. 分析训练效果
echo ============================================================
echo [3/3] 分析训练效果
echo ============================================================
python src/train/analyze_training_effectiveness.py
if errorlevel 1 (
    echo [警告] 分析过程出现错误
)
echo.

echo ============================================================
echo 评估完成！
echo ============================================================
echo.
echo 评估结果已显示在上方。
echo 建议查看详细报告文档：
echo   - docs/training/训练完成最终报告.md
echo   - docs/training/训练效果最终分析.md
echo.
pause

