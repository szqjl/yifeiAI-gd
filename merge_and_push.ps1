# 合并本地有价值的改进并推送

Write-Host "开始处理本地改进..." -ForegroundColor Cyan

# 1. 对于execution_state.json，使用远程版本（远程更新）
Write-Host "`n1. 处理 execution_state.json (使用远程版本)" -ForegroundColor Yellow
git checkout origin/main -- execution_state.json
git add execution_state.json

# 2. 保留本地有价值的代码改进
Write-Host "`n2. 保留本地代码改进" -ForegroundColor Yellow
# utils.py - 本地有拆三张逻辑优化，保留
# yf1_v5.py, yf2_v5.py - 保留本地修改
# card_grouping_strategy.py - 保留本地修改
# multi_factor_evaluator.py - 已解决冲突，使用远程版本
# enhanced_state.py - 保留本地修改
# game_scores.json - 保留本地修改

# 3. 删除已删除的文件
Write-Host "`n3. 处理删除的文件" -ForegroundColor Yellow
git rm "docs/skill/掼蛋入门指南" 2>$null

# 4. 查看最终状态
Write-Host "`n4. 最终状态:" -ForegroundColor Yellow
git status --short

Write-Host "`n处理完成！" -ForegroundColor Green

