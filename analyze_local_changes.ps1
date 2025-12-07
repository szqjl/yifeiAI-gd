# 分析本地暂存文件与远程版本的差异
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "本地暂存文件 vs 远程版本对比分析" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$files = @(
    "execution_state.json",
    "game_scores.json",
    "src/communication/utils.py",
    "src/communication/yf1_v5.py",
    "src/communication/yf2_v5.py",
    "src/decision/card_grouping_strategy.py",
    "src/decision/multi_factor_evaluator.py",
    "src/game_logic/enhanced_state.py"
)

foreach ($file in $files) {
    Write-Host "`n分析文件: $file" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Gray
    
    # 获取本地和远程的修改时间
    $localTime = git log -1 --format="%ai" HEAD -- $file 2>$null
    $remoteTime = git log -1 --format="%ai" origin/main -- $file 2>$null
    
    Write-Host "本地最后修改: $localTime" -ForegroundColor White
    Write-Host "远程最后修改: $remoteTime" -ForegroundColor White
    
    # 获取差异统计
    $diffStat = git diff --cached origin/main --stat -- $file 2>$null
    if ($diffStat) {
        Write-Host "差异统计: $diffStat" -ForegroundColor Cyan
    }
    
    # 检查是否有实际代码逻辑变化
    $diffContent = git diff --cached origin/main -- $file 2>$null | Select-String -Pattern "def |class |if |return |# " | Select-Object -First 5
    if ($diffContent) {
        Write-Host "关键变化:" -ForegroundColor Green
        $diffContent | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "分析完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

