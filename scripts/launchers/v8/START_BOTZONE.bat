@echo off
REM V8 Botzone 在线监听（凭据从环境变量读取，勿在文件中写密钥）
REM   set BOTZONE_USER_ID=your_user_id
REM   set BOTZONE_API_KEY=your_api_key
REM   set BOTZONE_TEAMMATE_BOT_ID=optional_teammate_bot_id
cd /d %~dp0..\..\..
set PYTHONIOENCODING=utf-8
if "%BOTZONE_USER_ID%"=="" (
  echo ERROR: set BOTZONE_USER_ID
  exit /b 1
)
if "%BOTZONE_API_KEY%"=="" (
  echo ERROR: set BOTZONE_API_KEY
  exit /b 1
)
set LOG=logs\v8_vs_botzone_%date:~0,4%%date:~5,2%%date:~8,2%_single.log
if not "%BOTZONE_TEAMMATE_BOT_ID%"=="" (
  python scripts\launchers\v8\run_v8_vs_botzone.py --user-id %BOTZONE_USER_ID% --api-key %BOTZONE_API_KEY% --teammate-bot-id %BOTZONE_TEAMMATE_BOT_ID% >> %LOG% 2>&1
) else (
  python scripts\launchers\v8\run_v8_vs_botzone.py --user-id %BOTZONE_USER_ID% --api-key %BOTZONE_API_KEY% >> %LOG% 2>&1
)
