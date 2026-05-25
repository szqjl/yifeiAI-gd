param(
    [string]$EventKey = "im.message.receive_v1",
    [int]$Timeout = 0
)

$ProfileName = "yife-gd-bot"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  yife-gd-bot - Lark Bot Event Consumer" -ForegroundColor Cyan
Write-Host "  Profile: $ProfileName" -ForegroundColor Cyan
Write-Host "  Event:   $EventKey" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$argsList = @(
    "event", "consume", $EventKey,
    "--profile", $ProfileName,
    "--as", "bot"
)

if ($Timeout -gt 0) {
    $argsList += "--timeout"
    $argsList += "${Timeout}s"
}

Write-Host "Starting event consumer (PID: $PID)..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

& "lark-cli" $argsList
