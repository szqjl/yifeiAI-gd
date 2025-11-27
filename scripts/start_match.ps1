# 掼蛋AI比赛启动脚本
# 使用: .\scripts\start_match.ps1

$ServerDir = "D:\guandan_offline_v1006\windows"
$ServerExe = "guandan_offline_v1006.exe"
$ServerWaitTime = 15
$ClientStartInterval = 3

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
if (-not (Test-Path $ProjectRoot)) {
    $ProjectRoot = "D:\guandanscore\YiFeiAI-GD"
}
Set-Location $ProjectRoot

$Clients = @(
    @{Name="client1"; File="Test1.py"; Path="src\communication\Test1.py"; Team="队伍1"; Seat=0},
    @{Name="client3"; File="client3.py"; Path="src\communication\client3.py"; Team="队伍2"; Seat=1},
    @{Name="client2"; File="Test2.py"; Path="src\communication\Test2.py"; Team="队伍1"; Seat=2},
    @{Name="client4"; File="client4.py"; Path="src\communication\client4.py"; Team="队伍2"; Seat=3}
)

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  掼蛋AI比赛启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动时间: $timestamp" -ForegroundColor Gray
Write-Host "项目目录: $ProjectRoot" -ForegroundColor Gray
Write-Host ""

Write-Host "[1/4] 检查依赖..." -ForegroundColor Yellow
try {
    pip install --quiet --upgrade ws4py websockets pyyaml 2>&1 | Out-Null
    Write-Host "  OK 依赖检查完成" -ForegroundColor Green
} catch {
    Write-Host "  WARN 依赖检查失败，继续执行..." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[2/4] 检查路径..." -ForegroundColor Yellow
if (-not (Test-Path $ServerDir)) {
    Write-Host "  ERROR 服务器目录不存在: $ServerDir" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}
if (-not (Test-Path (Join-Path $ServerDir $ServerExe))) {
    Write-Host "  ERROR 服务器可执行文件不存在" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}
Write-Host "  OK 路径检查通过" -ForegroundColor Green
Write-Host ""

Write-Host "[3/4] 启动服务器..." -ForegroundColor Yellow
Get-Process -Name "guandan_offline_v1006" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

try {
    $serverProcess = Start-Process -FilePath $ServerExe -WorkingDirectory $ServerDir -WindowStyle Normal -PassThru
    if (-not $serverProcess) {
        Write-Host "  ERROR 服务器启动失败" -ForegroundColor Red
        Read-Host "按 Enter 退出"
        exit 1
    }
    Write-Host "  OK 服务器已启动 (PID: $($serverProcess.Id))" -ForegroundColor Green
    Write-Host "  等待服务器初始化 ($ServerWaitTime 秒)..." -ForegroundColor Gray
    Start-Sleep -Seconds $ServerWaitTime
    Write-Host "  OK 服务器就绪" -ForegroundColor Green
} catch {
    Write-Host "  ERROR 服务器启动失败: $_" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}
Write-Host ""

Write-Host "[4/4] 启动客户端..." -ForegroundColor Yellow
$clientProcesses = @()

foreach ($client in $Clients) {
    $clientPath = Join-Path $ProjectRoot $client.Path
    
    if (-not (Test-Path $clientPath)) {
        Write-Host "  ERROR $($client.Name) 文件不存在: $clientPath" -ForegroundColor Red
        continue
    }
    
    Write-Host "  启动 $($client.Name) ($($client.File)) - $($client.Team), 座位$($client.Seat)..." -ForegroundColor Cyan
    
    try {
        $cmd = "Set-Location '$ProjectRoot'; Write-Host '[$($client.Name)] 启动中...' -ForegroundColor Cyan; python '$($client.Path)'"
        $proc = Start-Process pwsh.exe -ArgumentList "-NoExit", "-Command", $cmd -WindowStyle Normal -PassThru
        
        if ($proc) {
            $clientProcesses += @{Name=$client.Name; PID=$proc.Id; Process=$proc}
            Write-Host "    OK 已启动 (PID: $($proc.Id))" -ForegroundColor Green
        } else {
            Write-Host "    ERROR 启动失败" -ForegroundColor Red
        }
    } catch {
        Write-Host "    ERROR 启动失败: $_" -ForegroundColor Red
    }
    
    if ($client -ne $Clients[-1]) {
        Start-Sleep -Seconds $ClientStartInterval
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  所有客户端已启动！比赛开始" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "队伍分组:" -ForegroundColor Yellow
Write-Host "  队伍1 (知识库增强): 座位0(client1) + 座位2(client2)" -ForegroundColor Cyan
Write-Host "  队伍2 (硬编码规则): 座位1(client3) + 座位3(client4)" -ForegroundColor Magenta
Write-Host ""

Write-Host "进程信息:" -ForegroundColor Yellow
Write-Host "  服务器 PID: $($serverProcess.Id)" -ForegroundColor White
foreach ($c in $clientProcesses) {
    Write-Host "  $($c.Name) PID: $($c.PID)" -ForegroundColor White
}
Write-Host ""

$info = @{
    timestamp = $timestamp
    server_pid = $serverProcess.Id
    clients = $clientProcesses | ForEach-Object { @{name=$_.Name; pid=$_.PID} }
} | ConvertTo-Json -Depth 3

$info | Out-File -FilePath "match_process_info.json" -Encoding UTF8
Write-Host "进程信息已保存到: match_process_info.json" -ForegroundColor Gray
Write-Host ""

Write-Host "提示:" -ForegroundColor Yellow
Write-Host "  - 查看各PowerShell窗口的输出日志" -ForegroundColor Gray
Write-Host "  - 使用 Alt+Tab 切换窗口查看" -ForegroundColor Gray
Write-Host "  - 按 Ctrl+C 退出监控（进程继续运行）" -ForegroundColor Gray
Write-Host ""

Write-Host "比赛进行中，监控进程状态..." -ForegroundColor Yellow
try {
    while ($true) {
        Start-Sleep -Seconds 10
        
        if (-not (Get-Process -Id $serverProcess.Id -ErrorAction SilentlyContinue)) {
            Write-Host "WARN 服务器进程已结束" -ForegroundColor Red
            break
        }
        
        $dead = @()
        foreach ($c in $clientProcesses) {
            if (-not (Get-Process -Id $c.PID -ErrorAction SilentlyContinue)) {
                $dead += $c.Name
            }
        }
        if ($dead.Count -gt 0) {
            Write-Host "WARN 客户端进程已结束: $($dead -join ', ')" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "`n监控已退出" -ForegroundColor Gray
}
