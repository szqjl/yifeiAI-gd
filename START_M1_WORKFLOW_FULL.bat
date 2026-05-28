@echo off
chcp 65001 >nul
REM M1完整训练工作流启动脚本
REM 包含：自动对战、MLflow实时监控、自动代码优化
REM 唯一目标：M1战胜client

echo ==========================================
echo M1完整训练工作流
echo 目标：训练直到M1战胜client（胜率^>50%%）
echo ==========================================
echo.

echo 工作流功能：
echo   1. 自动运行M1与client对战生成记录
echo   2. 训练模型（MLflow实时监控）
echo   3. 从MLflow读取实时指标
echo   4. 根据MLflow指标自动优化训练代码
echo   5. 评估M1 vs Client胜率
echo   6. 迭代直到胜率^>50%%
echo.

REM 设置参数
set MAX_ITERATIONS=10
set TARGET_WIN_RATE=0.50
set MIN_GAMES=50
set SERVER_PATH=D:\GDAI\server\windows\guandan_offline_v1006.exe

echo 工作流配置:
echo   最大迭代次数: %MAX_ITERATIONS%
echo   目标胜率: %TARGET_WIN_RATE% (50%%)
echo   评估对局数: %MIN_GAMES%
echo   游戏服务器: %SERVER_PATH%
echo.

echo 提示：可在新终端运行以下命令查看MLflow实时监控：
echo   mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns
echo   然后浏览器打开 http://localhost:5000
echo.

REM 运行完整工作流
python src/train/m1_training_workflow.py ^
    --max_iterations %MAX_ITERATIONS% ^
    --target_win_rate %TARGET_WIN_RATE% ^
    --min_games %MIN_GAMES% ^
    --server_path "%SERVER_PATH%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo ✅ 工作流成功完成！M1已能战胜client
    echo ==========================================
    echo.
    echo 查看成功通知:
    echo   models\M1_TARGET_ACHIEVED.txt
    echo.
    echo 运行以下命令查看详细状态:
    echo   python scripts/checks/check_workflow_notification.py
    echo.
) else (
    echo.
    echo ==========================================
    echo ⚠️ 工作流未完全达成目标
    echo 请查看日志了解详情
    echo ==========================================
    echo.
    echo 运行以下命令查看详细状态:
    echo   python scripts/checks/check_workflow_notification.py
    echo.
)

echo.
echo 查看工作流历史:
echo   models\m1_training_workflow_history.json
echo.
echo 查看MLflow监控:
echo   mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns
echo.
pause
