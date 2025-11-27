﻿# 掼蛋AI比赛自动启动脚本 - Test1、2 vs 一等奖client3、4
# 使用: .\scripts\start_match_test12_vs_firstprize34.ps1
# 队伍配置: Test1 + Test2 (知识库增强) vs 一等奖client3 + client4 (一等奖代码)
# 启动顺序确保座位: 0(client1) + 2(client2) vs 1(client3) + 3(client4)

# ========================================
# 设置字符编码为 UTF-8（根据 PowerShell 7.x 最佳实践）
# ========================================
# 设置控制台输入/输出编码为 UTF-8
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 设置所有文件操作的默认编码为 UTF-8（根据 Microsoft 文档建议）
# 这确保 Get-Content、Out-File 等 cmdlet 使用 UTF-8 编码
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

# ========================================
# 自动导航到项目根目录
# ========================================
# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# 脚本在 scripts 目录下，项目根目录是上一级
$ProjectRoot = Split-Path -Parent $ScriptDir

# 如果自动检测失败，使用硬编码路径作为备选
if (-not (Test-Path $ProjectRoot)) {
    Write-Host "警告: 自动检测项目目录失败，使用硬编码路径" -ForegroundColor Yellow
    $ProjectRoot = "D:\guandanscore\YiFeiAI-GD"
}

# 导航到项目根目录
Write-Host "正在导航到项目目录..." -ForegroundColor Gray
Write-Host "脚本位置: $ScriptDir" -ForegroundColor Gray
Write-Host "项目根目录: $ProjectRoot" -ForegroundColor Gray

try {
    Set-Location $ProjectRoot
    Write-Host "[OK] 已导航到项目根目录" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] 导航失败: $_" -ForegroundColor Red
    Write-Host "请手动切换到项目根目录: $ProjectRoot" -ForegroundColor Yellow
    Read-Host "按 Enter 键退出"
    exit 1
}

# 验证项目根目录是否正确（检查是否存在 src 目录）
if (-not (Test-Path (Join-Path $ProjectRoot "src"))) {
    Write-Host "错误: 项目根目录不正确，未找到 src 目录" -ForegroundColor Red
    Write-Host "当前目录: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "请确认项目根目录路径是否正确" -ForegroundColor Yellow
    Read-Host "按 Enter 键退出"
    exit 1
}

# 获取当前时间戳
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "掼蛋AI比赛启动脚本 - Test1、2 vs 一等奖client3、4" -ForegroundColor Cyan
Write-Host "启动时间: $timestamp" -ForegroundColor Gray
Write-Host "项目目录: $ProjectRoot" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置路径（使用绝对路径）
$ServerDir = "D:\guandan_offline_v1006\windows"
$ServerExe = "guandan_offline_v1006.exe"

# 客户端配置
# 启动顺序: client1 (座位0) → client3 (座位1) → client2 (座位2，同队0) → client4 (座位3，同队1)
$ClientConfigs = @(
    @{Name="client1"; Script="Test1.py"; Path="src\communication\Test1.py"; Team="队伍1-知识库增强"; Seat=0},
    @{Name="client3"; Script="client3.py"; Path="src\communication\first_prize\client3.py"; Team="队伍2-一等奖代码"; Seat=1},
    @{Name="client2"; Script="Test2.py"; Path="src\communication\Test2.py"; Team="队伍1-知识库增强"; Seat=2},
    @{Name="client4"; Script="client4.py"; Path="src\communication\first_prize\client4.py"; Team="队伍2-一等奖代码"; Seat=3}
)

# 工作目录已在脚本开头设置
Write-Host "当前工作目录: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# 检查并安装必要依赖
Write-Host "1. 检查并安装依赖..." -ForegroundColor Yellow
try {
    pip install --upgrade ws4py websockets pyyaml 2>&1 | Out-Null
    Write-Host "   [OK] 依赖检查完成" -ForegroundColor Green
} catch {
    Write-Host "   [ERROR] 依赖安装失败: $_" -ForegroundColor Red
}
Write-Host ""

# 检查服务器目录是否存在
if (-not (Test-Path $ServerDir)) {
    Write-Host "错误: 服务器目录不存在: $ServerDir" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

if (-not (Test-Path (Join-Path $ServerDir $ServerExe))) {
    Write-Host "错误: 服务器可执行文件不存在: $(Join-Path $ServerDir $ServerExe)" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

# 启动服务器
Write-Host "2. 启动离线平台服务器..." -ForegroundColor Yellow
try {
    # 先尝试关闭可能存在的旧服务器进程
    $oldServer = Get-Process -Name "guandan_offline_v1006" -ErrorAction SilentlyContinue
    if ($oldServer) {
        Write-Host "   检测到已有服务器进程，正在关闭..." -ForegroundColor Gray
        Stop-Process -Name "guandan_offline_v1006" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    
    # 启动服务器（使用Normal窗口样式，可见）
    $serverProcess = Start-Process -FilePath $ServerExe -WorkingDirectory $ServerDir -WindowStyle Normal -PassThru
    if ($serverProcess) {
        Write-Host "   [OK] 服务器进程已启动 (PID: $($serverProcess.Id))" -ForegroundColor Green
    } else {
        Write-Host "   [OK] 服务器启动失败" -ForegroundColor Red
        Read-Host "按 Enter 键退出"
        exit 1
    }
} catch {
    Write-Host "   [OK] 服务器启动失败: $_" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

# 等待服务器启动
Write-Host "   等待服务器初始化 (15秒)..." -ForegroundColor Gray
Start-Sleep -Seconds 15
Write-Host "   [OK] 服务器启动完成，等待客户端连接..." -ForegroundColor Green
Write-Host ""

# 启动四个客户端
Write-Host "3. 启动客户端..." -ForegroundColor Yellow
$clientProcesses = @()
$clientIndex = 0

foreach ($client in $ClientConfigs) {
    $clientIndex++
    $clientPath = Join-Path $ProjectRoot $client.Path
    
    # 检查客户端文件是否存在
    if (-not (Test-Path $clientPath)) {
        Write-Host "   [OK] 客户端文件不存在: $clientPath" -ForegroundColor Red
        continue
    }
    
    Write-Host "   [$clientIndex/4] 启动 $($client.Name) ($($client.Script)) - $($client.Team), 预期座位: $($client.Seat)" -ForegroundColor Cyan
    
    try {
        # 启动客户端（每个在单独的PowerShell窗口，使用Normal窗口样式，可见）
        $clientProc = Start-Process pwsh.exe -ArgumentList @(
            "-NoExit",
            "-Command",
            "Set-Location '$ProjectRoot'; Write-Host '[$($client.Name)] 启动中...' -ForegroundColor Cyan; python '$($client.Path)'"
        ) -WindowStyle Normal -PassThru
        
        if ($clientProc) {
            $clientProcesses += @{
                Name = $client.Name
                Process = $clientProc
                PID = $clientProc.Id
            }
            Write-Host "      [OK] 客户端 $($client.Name) 已启动 (PID: $($clientProc.Id))" -ForegroundColor Green
        } else {
            Write-Host "      [OK] 客户端 $($client.Name) 启动失败" -ForegroundColor Red
        }
    } catch {
        Write-Host "      [OK] 客户端 $($client.Name) 启动失败: $_" -ForegroundColor Red
    }
    
    # 间隔启动避免连接冲突
    if ($clientIndex -lt $ClientConfigs.Count) {
        Start-Sleep -Seconds 3
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "所有客户端已启动！比赛开始。" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 显示队伍分组信息
Write-Host "=== 队伍分组 ===" -ForegroundColor Yellow
Write-Host "队伍1 (知识库增强 AI):" -ForegroundColor Cyan
Write-Host "  - 座位0: client1 (Test1.py)" -ForegroundColor White
Write-Host "  - 座位2: client2 (Test2.py)" -ForegroundColor White
Write-Host ""
Write-Host "队伍2 (一等奖代码 AI):" -ForegroundColor Magenta
Write-Host "  - 座位1: client3 (一等奖代码)" -ForegroundColor White
Write-Host "  - 座位3: client4 (一等奖代码)" -ForegroundColor White
Write-Host ""

# 显示进程信息
Write-Host "=== 进程信息 ===" -ForegroundColor Yellow
Write-Host "服务器进程 PID: $($serverProcess.Id)" -ForegroundColor White
foreach ($clientInfo in $clientProcesses) {
    Write-Host "$($clientInfo.Name) 进程 PID: $($clientInfo.PID)" -ForegroundColor White
}
Write-Host ""

# 监控提示
Write-Host "=== 监控提示 ===" -ForegroundColor Yellow
Write-Host "- 检查各PowerShell窗口的输出日志" -ForegroundColor Gray
Write-Host "- 预期日志: 每个客户端 '[clientX] Connected successfully!'" -ForegroundColor Gray
Write-Host "- 比赛结果: episodeOver/gameResult 显示胜负、剩余牌" -ForegroundColor Gray
Write-Host "- 如果连接失败: 检查日志，重启脚本" -ForegroundColor Gray
Write-Host "- 停止比赛: 关闭所有PowerShell窗口或使用任务管理器结束进程" -ForegroundColor Gray
Write-Host ""
Write-Host "=== 如何找到窗口 ===" -ForegroundColor Yellow
Write-Host "1. 服务器窗口: 查找标题包含 'guandan_offline_v1006' 的窗口" -ForegroundColor Cyan
Write-Host "2. 客户端窗口: 查找标题为 'PowerShell' 的窗口（应该有4个）" -ForegroundColor Cyan
Write-Host "3. 如果看不到窗口，请:" -ForegroundColor Cyan
Write-Host "   - 检查任务栏是否有最小化的窗口" -ForegroundColor White
Write-Host "   - 使用 Alt+Tab 切换窗口查看" -ForegroundColor White
Write-Host "   - 使用任务管理器查看进程（PID已显示在上方）" -ForegroundColor White
Write-Host ""

# 保存进程信息到文件
$processInfo = @{
    timestamp = $timestamp
    server_pid = $serverProcess.Id
    clients = $clientProcesses | ForEach-Object { @{name=$_.Name; pid=$_.PID} }
} | ConvertTo-Json -Depth 3

$logFile = Join-Path $ProjectRoot "match_process_info.json"
$processInfo | Out-File -FilePath $logFile -Encoding UTF8
Write-Host "进程信息已保存到: $logFile" -ForegroundColor Gray
Write-Host ""

# 尝试将窗口带到前台（如果被最小化）
Write-Host "=== 窗口管理 ===" -ForegroundColor Yellow
Write-Host "正在尝试将窗口显示到前台..." -ForegroundColor Gray
Start-Sleep -Seconds 2

# 定义Win32 API用于窗口操作（只定义一次）
try {
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Win32Window {
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        public static int SW_RESTORE = 9;
        public static int SW_SHOW = 5;
    }
"@ -ErrorAction SilentlyContinue
} catch {
    # 如果已经定义过，忽略错误
}

# 尝试激活服务器窗口
try {
    $serverWindow = Get-Process -Id $serverProcess.Id -ErrorAction SilentlyContinue
    if ($serverWindow -and $serverWindow.MainWindowHandle -ne [IntPtr]::Zero) {
        [Win32Window]::ShowWindow($serverWindow.MainWindowHandle, [Win32Window]::SW_RESTORE)
        [Win32Window]::SetForegroundWindow($serverWindow.MainWindowHandle)
        Write-Host "   [OK] 服务器窗口已激活" -ForegroundColor Green
    }
} catch {
    Write-Host "   提示: 服务器窗口可能不在前台，请检查任务栏" -ForegroundColor Gray
}

# 尝试激活客户端窗口
$activatedCount = 0
foreach ($clientInfo in $clientProcesses) {
    try {
        $clientWindow = Get-Process -Id $clientInfo.PID -ErrorAction SilentlyContinue
        if ($clientWindow -and $clientWindow.MainWindowHandle -ne [IntPtr]::Zero) {
            [Win32Window]::ShowWindow($clientWindow.MainWindowHandle, [Win32Window]::SW_RESTORE)
            $activatedCount++
        }
    } catch {
        # 忽略错误
    }
}

if ($activatedCount -gt 0) {
    Write-Host "   [OK] 已激活 $activatedCount 个客户端窗口" -ForegroundColor Green
}
Write-Host "   提示: 如果窗口不在前台，请从任务栏中点击相应的PowerShell窗口" -ForegroundColor Gray
Write-Host "   窗口标题: 服务器窗口显示 'guandan_offline_v1006'，客户端窗口显示 'PowerShell'" -ForegroundColor Gray
Write-Host ""

# 保持脚本运行以监控（可选，按 Ctrl+C 退出）
Write-Host "比赛进行中... 按 Ctrl+C 退出脚本（进程将继续运行）" -ForegroundColor Yellow
try {
    while ($true) {
        Start-Sleep -Seconds 10
        
        # 检查服务器进程是否还在运行
        $serverRunning = Get-Process -Id $serverProcess.Id -ErrorAction SilentlyContinue
        if (-not $serverRunning) {
            Write-Host "警告: 服务器进程已结束" -ForegroundColor Red
            break
        }
        
        # 检查客户端进程
        $deadClients = @()
        foreach ($clientInfo in $clientProcesses) {
            $clientRunning = Get-Process -Id $clientInfo.PID -ErrorAction SilentlyContinue
            if (-not $clientRunning) {
                $deadClients += $clientInfo.Name
            }
        }
        
        if ($deadClients.Count -gt 0) {
            Write-Host "警告: 以下客户端进程已结束: $($deadClients -join ', ')" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "`n脚本已退出" -ForegroundColor Gray
}

