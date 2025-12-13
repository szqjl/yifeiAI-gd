# 训练监控脚本
Write-Host "=== 阶段5优化训练监控 ===" -ForegroundColor Cyan
Write-Host ""

# 检查训练进程
$procs = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmd = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmd -like "*train_stage5_optimized*"
}

if ($procs) {
    Write-Host "✓ 训练进程正在运行" -ForegroundColor Green
    foreach ($proc in $procs) {
        $runtime = (Get-Date) - $proc.StartTime
        Write-Host "  进程ID: $($proc.Id)"
        Write-Host "  运行时间: $($runtime.Hours)小时 $($runtime.Minutes)分钟 $($runtime.Seconds)秒"
        Write-Host "  CPU时间: $([math]::Round($proc.CPU, 2)) 秒"
        Write-Host "  内存: $([math]::Round($proc.WorkingSet/1MB, 2)) MB"
    }
} else {
    Write-Host "✗ 未找到训练进程" -ForegroundColor Red
}

Write-Host ""

# 检查日志文件
$logFiles = Get-ChildItem training_logs/stage5_training_optimized_*.log -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
if ($logFiles) {
    $latest = $logFiles[0]
    Write-Host "✓ 日志文件已创建" -ForegroundColor Green
    Write-Host "  文件: $($latest.Name)"
    Write-Host "  大小: $([math]::Round($latest.Length/1KB, 2)) KB"
    Write-Host "  最后更新: $($latest.LastWriteTime)"
    Write-Host ""
    Write-Host "=== 最新输出（最后30行）===" -ForegroundColor Yellow
    Get-Content $latest.FullName -Tail 30
} else {
    Write-Host "⚠ 日志文件尚未创建" -ForegroundColor Yellow
    Write-Host "  训练可能还在初始化或数据加载阶段..."
}

Write-Host ""

# 检查模型文件
if (Test-Path "models/bc_model_stage5_optimized.pth") {
    $model = Get-Item "models/bc_model_stage5_optimized.pth"
    Write-Host "✓ 模型文件已生成" -ForegroundColor Green
    Write-Host "  大小: $([math]::Round($model.Length/1MB, 2)) MB"
    Write-Host "  最后修改: $($model.LastWriteTime)"
} else {
    Write-Host "⚠ 模型文件尚未生成" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "按任意键刷新监控，或 Ctrl+C 退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

