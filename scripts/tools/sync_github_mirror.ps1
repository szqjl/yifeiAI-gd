# GitHub 镜像维护（develop 清理 + m-dev 同步）
#
# 前提：已配置 `git remote github` 且本机可访问 GitHub。
# 真相源：Gitee `origin`（日常只 push origin）。
#
# 用法（仓库根）：
#   powershell -ExecutionPolicy Bypass -File scripts/tools/sync_github_mirror.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

function Invoke-Git {
    param([string[]]$GitArgs)
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "git $($GitArgs -join ' ') failed ($LASTEXITCODE)" }
}

Write-Host "==> git fetch github --prune"
Invoke-Git fetch, github, --prune

$developHead = git ls-remote --heads github develop 2>$null
if ($developHead) {
    Write-Host "==> delete github/develop"
    Invoke-Git push, github, --delete, develop
} else {
    Write-Host "==> github/develop 不存在（已清理或从未创建）"
}

Write-Host "==> push m-dev -> github/m-dev"
Invoke-Git push, github, m-dev:m-dev

Write-Host "==> 完成。可在 GitHub 将默认分支设为 m-dev（若仍为 main/m1-dev）。"
Write-Host "    日常开发仍只 push: git push origin m-dev"
