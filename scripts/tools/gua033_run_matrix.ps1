# GUA-033 净盘矩阵：target-games 1 / 3 / 10
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..
$Server = "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"
$Clients = @(
    "src/communication/yf1_m3.py",
    "src/communication/run_lalala_client3.py",
    "src/communication/yf2_m3.py",
    "src/communication/run_lalala_client4.py"
)
$env:BATCH_EXECUTOR_SECONDS_PER_GAME_ESTIMATE = "120"
$env:BATCH_EXECUTOR_MIN_BATCH_SECONDS = "60"

function Clear-RunArtifacts {
    Get-Process guandan_offline_v1006 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Remove-Item tmp\.batch_executor.lock -ErrorAction SilentlyContinue
    Get-ChildItem game_records -Filter *.json -ErrorAction SilentlyContinue | Remove-Item -Force
    Remove-Item execution_state.json -ErrorAction SilentlyContinue
    Remove-Item batch_executor\latest_victory_num.json -ErrorAction SilentlyContinue
    Remove-Item batch_executor\current_batch.json -ErrorAction SilentlyContinue
    Get-ChildItem logs -File -ErrorAction SilentlyContinue | Remove-Item -Force
}

foreach ($tg in @(1, 3, 10)) {
    Write-Host "`n========== target-games $tg ==========" -ForegroundColor Cyan
    Clear-RunArtifacts
    python -m batch_executor.main `
        --server-path $Server `
        --target-games $tg `
        --clients @Clients `
        --state-file execution_state.json `
        --score-file game_scores_m2.json
    if ($LASTEXITCODE -ne 0) { Write-Warning "batch failed for target=$tg exit=$LASTEXITCODE" }
    python scripts/tools/gua033_collect_batch_evidence.py $tg | Out-File -Encoding utf8 "data/eval/gua033_matrix_$tg.json"
    Copy-Item batch_executor\current_batch.json "data/eval/gua033_batch_ctx_$tg.json" -ErrorAction SilentlyContinue
    Copy-Item batch_executor\latest_victory_num.json "data/eval/gua033_latest_vn_$tg.json" -ErrorAction SilentlyContinue
}

Write-Host "`nDone. See data/eval/gua033_matrix_*.json" -ForegroundColor Green
