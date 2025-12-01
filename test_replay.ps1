# 测试回放工具
Write-Host "Testing Replay Tool..." -ForegroundColor Green

# 设置环境
$scriptDir = "D:\guandanscore\YiFeiAI-GD"
Set-Location $scriptDir
$env:PYTHONPATH = "$scriptDir\src"

# 测试导入
Write-Host "`n[1] Testing imports..." -ForegroundColor Yellow
python -c "import sys; sys.path.insert(0, r'$scriptDir\src'); from communication.replay_game import list_games; print('✓ Import successful')"

# 测试列出游戏记录
Write-Host "`n[2] Testing list games..." -ForegroundColor Yellow
python -c "import sys; sys.path.insert(0, r'$scriptDir\src'); from communication.replay_game import list_games; games = list_games(); print(f'✓ Found {len(games)} game records')"

# 测试选择脚本
Write-Host "`n[3] Testing replay_select.py..." -ForegroundColor Yellow
python "$scriptDir\src\communication\replay_select.py" 2>&1 | Select-Object -First 3

Write-Host "`n✓ All tests completed!" -ForegroundColor Green

