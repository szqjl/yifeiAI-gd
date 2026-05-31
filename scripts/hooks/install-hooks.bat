@echo off
setlocal
cd /d "%~dp0..\.."
echo ============================================================
echo 安装 Git hooks（pre-push 治理校验）
echo ============================================================
echo.

if not exist ".git" (
    echo ERROR: 请在仓库根目录运行
    exit /b 1
)

git config core.hooksPath scripts/hooks
if errorlevel 1 (
    echo ERROR: git config core.hooksPath 失败
    exit /b 1
)

echo 已设置: core.hooksPath = scripts/hooks
echo.
echo 推送时将自动:
echo   - 禁止 push 到 main
echo   - 检查 Layer 2 大文件 / 产物路径
echo.
echo Agent 仍须阅读:
echo   docs/governance/M-V-Series-治理方案.md
echo   docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
echo.
echo 本机一次性执行即可；换克隆后需重跑本脚本。
pause
