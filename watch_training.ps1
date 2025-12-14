# 实时监控训练进度
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "训练进度实时监控" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$checkpoints = Get-ChildItem "models\bc_model_strategy_tasks_epoch_*.pth" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending

if ($checkpoints) {
    $latest = $checkpoints[0]
    $epochNum = [int]($latest.Name -replace '.*epoch_(\d+)\.pth', '$1')
    
    Write-Host "✓ 训练进行中" -ForegroundColor Green
    Write-Host "  当前进度: $epochNum/50 epochs ($([math]::Round($epochNum/50*100))%)" -ForegroundColor Yellow
    Write-Host "  最新检查点: $($latest.Name)" -ForegroundColor White
    Write-Host "  检查点大小: $([math]::Round($latest.Length/1MB, 2)) MB" -ForegroundColor White
    Write-Host "  最后更新: $($latest.LastWriteTime)" -ForegroundColor White
    Write-Host ""
    
    # 尝试读取检查点信息
    try {
        $pythonCmd = "import torch; ckpt = torch.load('models/$($latest.Name)', map_location='cpu'); print('Loss:', ckpt.get('loss', 'N/A')); print('Action Accuracy:', ckpt.get('action_exact_accuracy', 'N/A')); print('Strategy Accuracy:', ckpt.get('strategy_accuracy', 'N/A'))"
        $result = python -c $pythonCmd 2>&1
        if ($result) {
            Write-Host "  检查点信息:" -ForegroundColor Cyan
            $result | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        }
    } catch {
        Write-Host "  (无法读取检查点详细信息)" -ForegroundColor Gray
    }
} else {
    Write-Host "✗ 尚未生成检查点" -ForegroundColor Red
    Write-Host "  训练可能刚刚开始或尚未启动" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "提示: 训练完成后会生成最终模型" -ForegroundColor Cyan
Write-Host "      models/bc_model_strategy_tasks.pth" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

