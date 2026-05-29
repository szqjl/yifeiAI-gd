@echo off
call "%~dp0..\_env.bat"
REM 批量转换.rep文件为训练数据
REM 使用方法: batch_convert_replays.bat [最大文件数]


echo ============================================================
echo 批量转换.rep文件为训练数据
echo ============================================================
echo.

REM 设置参数
set MAX_FILES=%1
if "%MAX_FILES%"=="" set MAX_FILES=1000

echo 最大转换文件数: %MAX_FILES%
echo 输出目录: game_records
echo 优先选择获胜玩家: 是
echo.

REM 运行转换脚本
python src/knowledge_processor/batch_convert_replays.py --max_files %MAX_FILES% --prefer_winner --skip-existing

echo.
echo 转换完成！按任意键退出...
pause >nul

