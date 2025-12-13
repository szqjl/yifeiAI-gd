# 快速检查训练进度
Write-Host "=== 阶段5优化训练监控 ===" -ForegroundColor Cyan

# 检查日志文件
$logFiles = Get-ChildItem training_logs/stage5_optimized_*.log -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
if ($logFiles) {
    $latest = $logFiles[0]
    Write-Host "`n✓ 日志文件已创建" -ForegroundColor Green
    Write-Host "  文件: $($latest.Name)"
    Write-Host "  大小: $([math]::Round($latest.Length/1KB, 2)) KB"
    Write-Host "  最后更新: $($latest.LastWriteTime)"
    Write-Host "`n=== 最新输出 ===" -ForegroundColor Yellow
    Get-Content $latest.FullName -Tail 30
} else {
    Write-Host "`n⚠ 日志文件尚未创建" -ForegroundColor Yellow
}

# 检查训练进程
$procs = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmd = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmd -like "*train_stage5_optimized*"
}
if ($procs) {
    Write-Host "`n✓ 训练进程正在运行" -ForegroundColor Green
    foreach ($proc in $procs) {
        $runtime = (Get-Date) - $proc.StartTime
        Write-Host "  PID: $($proc.Id), 运行时间: $($runtime.Hours)h $($runtime.Minutes)m $($runtime.Seconds)s, CPU: $([math]::Round($proc.CPU, 2))s"
    }
} else {
    Write-Host "`n✗ 未找到训练进程" -ForegroundColor Red
}

# 检查模型文件
if (Test-Path "models/bc_model_stage5_optimized.pth") {
    $model = Get-Item "models/bc_model_stage5_optimized.pth"
    Write-Host "`n✓ 模型文件已生成" -ForegroundColor Green
    Write-Host "  大小: $([math]::Round($model.Length/1MB, 2)) MB"
    Write-Host "  时间: $($model.LastWriteTime)"
}

