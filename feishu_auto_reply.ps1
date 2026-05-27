$cli = "C:\Users\Jennifer\AppData\Roaming\npm\node_modules\@larksuite\cli\bin\lark-cli.exe"
$logFile = "$env:TEMP\feishu_events.txt"

# 清理旧日志
Remove-Item -Path $logFile -Force -ErrorAction SilentlyContinue

# 启动事件监听
$proc = Start-Process -FilePath $cli -ArgumentList "event +subscribe --event-types im.message.receive_v1 --compact --quiet --as bot" -NoNewWindow -RedirectStandardOutput $logFile -PassThru
Write-Output "Gateway PID: $($proc.Id)"

Write-Output "等待消息..."
while ($true) {
    Start-Sleep -Seconds 2
    if (Test-Path $logFile) {
        $lines = Get-Content $logFile
        foreach ($line in $lines) {
            try {
                $event = $line | ConvertFrom-Json
                if ($event.type -eq "im.message.receive_v1" -and $event.sender_id -ne "ou_b88219e7945c29d24475b4de1c9af0c1") {
                    # 只回复用户消息，不回复自己发的
                    continue
                }
                $msgId = $event.message_id
                $content = $event.content
                if ($msgId -and $content) {
                    Write-Output "收到: $content"
                    $reply = "收到你的消息: $content"
                    $replyJson = "{`"msg_type`":`"text`",`"content`":`"{`\`"text`\`":`\`"$reply`\`"}`"}"
                    $result = & $cli api POST "/open-apis/im/v1/messages/$msgId/reply" --data $replyJson --as bot --format json 2>&1
                    Write-Output "回复结果: $result"
                    # 清除已处理的消息
                    Set-Content $logFile -Value ""
                }
            } catch {
                Write-Output "解析失败: $_"
            }
        }
    }
}
