@echo off
call "%~dp0..\_env.bat"
echo 启动新的游戏测试...
python scripts/batch_executor.py ^
    --server-path "%REPO_ROOT%\offline_platform\guandan_offline_v1006\windows\guandan_offline_v1006.exe" ^
    --target-games 16 ^
    --clients src\communication\yf1_m1.py src\communication\run_lalala_client3.py src\communication\yf2_m1.py src\communication\run_lalala_client4.py
echo 测试完成，请重新运行验证脚本
pause
