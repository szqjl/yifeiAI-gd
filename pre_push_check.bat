@echo off
REM 推送前检查脚本 - 确保不会推送大文件
echo ============================================================
echo 推送前检查 - 确保不会推送大文件
echo ============================================================
echo.

REM 1. 检查暂存区
echo 1. 检查暂存区大文件...
git diff --cached --name-only > temp_staged.txt
python -c "import os; files = []; [files.extend([(line.strip(), os.path.getsize(line.strip())) for line in open('temp_staged.txt') if line.strip() and os.path.exists(line.strip()) and os.path.getsize(line.strip()) > 1024*1024]) for _ in [1]]; print(f'\n找到 {len(files)} 个大文件在暂存区:') if files else print('  ✓ 暂存区没有大文件'); [print(f'  ⚠️  {size/1024/1024:.2f}MB - {path}') for path, size in files[:10]]"
del temp_staged.txt 2>nul

echo.
echo 2. 检查工作区未跟踪的大文件...
git status --porcelain | findstr "^??" > temp_untracked.txt
python -c "import os, subprocess; files = []; [files.extend([(line[3:].strip(), os.path.getsize(line[3:].strip())) for line in open('temp_untracked.txt') if line.strip() and os.path.exists(line[3:].strip()) and os.path.getsize(line[3:].strip()) > 1024*1024]) for _ in [1]]; [files.append((f, s)) for f, s in files if subprocess.run(['git', 'check-ignore', f], capture_output=True).returncode != 0]; print(f'\n⚠️  发现 {len(files)} 个未跟踪且未被忽略的大文件:') if files else print('  ✓ 未跟踪的大文件都被正确忽略'); [print(f'  ⚠️  {size/1024/1024:.2f}MB - {path}') for path, size in files[:10]]"
del temp_untracked.txt 2>nul

echo.
echo 3. 治理校验（分支 + Layer 2）...
python scripts/hooks/pre_push_validate.py
if errorlevel 1 (
    echo.
    echo 校验失败。见 docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
    pause
    exit /b 1
)

echo.
echo 4. 验证.gitignore配置（若存在 verify_gitignore.py）...
if exist verify_gitignore.py (
    python verify_gitignore.py
) else (
    echo   跳过 verify_gitignore.py（未找到）
)

echo.
echo ============================================================
echo 检查完成！
echo ============================================================
pause

