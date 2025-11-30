# -*- coding: utf-8 -*-
# 游戏回放工具 - PowerShell版本

# 设置控制台编码为UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 设置工作目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 设置PYTHONPATH
$env:PYTHONPATH = Join-Path $scriptDir "src"

# 检查game_records目录
$recordDir = Join-Path $scriptDir "game_records"
if (-not (Test-Path $recordDir)) {
    Write-Host "[提示] 游戏记录目录不存在，正在创建..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $recordDir -Force | Out-Null
    Write-Host ""
}

# 显示标题
Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "游戏回放工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 选择回放模式
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "选择回放模式" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1] 基础回放模式 - 快速查看完整回放" -ForegroundColor White
Write-Host "[2] 交互式回放模式 - 支持上一步/下一步/自动播放（推荐）" -ForegroundColor White
Write-Host "[3] 退出" -ForegroundColor White
Write-Host ""

$mode = Read-Host "请选择模式 (1-3)"

if ($mode -eq "3") {
    exit 0
}

if ($mode -ne "1" -and $mode -ne "2") {
    Write-Host ""
    Write-Host "[错误] 无效的选择" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "正在加载游戏记录列表..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 执行Python脚本
$scriptPath = Join-Path $scriptDir "src\communication\replay_select.py"

if ($mode -eq "1") {
    python $scriptPath
} else {
    python $scriptPath --interactive
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[错误] 回放失败，请检查：" -ForegroundColor Red
    Write-Host "  1. Python环境和依赖是否完整" -ForegroundColor Yellow
    Write-Host "  2. 游戏记录文件是否存在" -ForegroundColor Yellow
    Write-Host "  3. 文件格式是否正确" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "回放完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车键退出"

