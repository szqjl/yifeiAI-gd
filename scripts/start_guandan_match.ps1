# 掼蛋AI比赛自动启动脚本 (队伍调整版)
# 使用: .\scripts\start_guandan_match.ps1
# 队伍配置: 知识队 (client1 + client2) vs 一等奖队 (client3 + client4)
# 启动顺序确保座位: 0(client1 知识) + 2(client2 知识) vs 1(client3 一等奖) + 3(client4 一等奖)

# 设置路径
$ProjectRoot = "D:\guandanscore\YiFeiAI-GD"
$ServerDir = "D:\掼蛋算法大赛选手人工智能代码\离线环境平台\windows"
$ServerExe = "guandan_offline_v1006.exe"
# 调整顺序: 知识 client1 (座位0) → 一等奖 client3 (座位1) → 知识 client2 (座位2，同队0) → 一等奖 client4 (座位3，同队1)
$Clients = @("client1.py", "client3.py", "client2.py", "client4.py")

# 切换到项目根目录
Set-Location $ProjectRoot

# 安装必要依赖 (如果未安装)
Write-Host "检查并安装依赖..."
try {
    pip install --upgrade ws4py websockets pyyaml
    Write-Host "依赖安装/更新完成。"
} catch {
    Write-Host "依赖安装失败: $_"
}

# 启动服务器 (使用 cd 切换目录后启动，避免路径问题)
Write-Host "启动离线平台服务器..."
try {
    $serverProcess = Start-Process pwsh.exe -ArgumentList "-NoExit", "-Command", "cd '$ServerDir'; Start-Process -FilePath '$ServerExe' -WindowStyle Hidden" -WindowStyle Hidden -PassThru
    if ($serverProcess) {
        Write-Host "服务器进程 PID: $($serverProcess.Id)"
    }
} catch {
    Write-Host "服务器启动失败: $_"
    return
}

# 等待服务器启动 (15 秒，确保端口 23456 可用)
Start-Sleep -Seconds 15
Write-Host "服务器启动完成，等待客户端连接..."

# 启动四个客户端 (每个在单独 PowerShell 进程，后台)
$clientProcesses = @()
foreach ($client in $Clients) {
    $clientPath = Join-Path "src\communication" $client
    Write-Host "启动客户端: $client (预期座位基于顺序)"
    try {
        $clientProc = Start-Process pwsh.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; python '$clientPath'" -WindowStyle Minimized -PassThru
        $clientProcesses += $clientProc
        Write-Host "客户端 $client 进程 PID: $($clientProc.Id)"
    } catch {
        Write-Host "客户端 $client 启动失败: $_"
    }
    Start-Sleep -Seconds 3  # 间隔启动避免连接冲突
}

Write-Host "所有客户端已启动！比赛开始。"
Write-Host "=== 队伍分组 ==="
Write-Host "- 知识增强队 (我们的 AI，使用知识库规则+技能): 座位0 (client1) + 座位2 (client2)"
Write-Host "- 一等奖队 (东南大学李菁 AI，使用硬编码规则): 座位1 (client3) + 座位3 (client4)"
Write-Host "- 预期: 知识队 vs 一等奖队，检验知识注入效果。"
Write-Host "=== 监控提示 ==="
Write-Host "- 检查 Cursor terminals 文件夹日志 (e.g., 新终端文件) 查看输出。"
Write-Host "- 预期日志: 每个客户端 '[clientX] Connected successfully!'、'我是 X 号位'、手牌、决策。"
Write-Host "- 知识影响: client1/client2 会基于 md 文件技能加分 (e.g., '对子技巧' 优先级高，偏好该动作)。"
Write-Host "- 比赛结果: episodeOver/gameResult 显示胜负、剩余牌。"
Write-Host "- 如果座位不对或连接失败: 检查日志，重启脚本。"
Write-Host "- 停止: 任务管理器结束 pwsh/python/guandan_offline_v1006.exe 进程。"

# 保持脚本运行以监控 (可选，按 Enter 退出)
Read-Host "按 Enter 键退出脚本 (进程继续运行)"
