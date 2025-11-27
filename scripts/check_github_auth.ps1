# GitHub 认证配置检查脚本
# 用途：检查GitHub远程仓库的认证配置状态

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub 认证配置检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查Git配置
Write-Host "1. 检查Git凭据助手配置..." -ForegroundColor Yellow
$credentialHelper = git config --global --get credential.helper
if ($credentialHelper) {
    Write-Host "   ? 凭据助手: $credentialHelper" -ForegroundColor Green
} else {
    Write-Host "   ? 未配置凭据助手" -ForegroundColor Red
    Write-Host "   建议运行: git config --global credential.helper manager-core" -ForegroundColor Yellow
}
Write-Host ""

# 2. 检查GitHub远程仓库
Write-Host "2. 检查GitHub远程仓库配置..." -ForegroundColor Yellow
$githubRemote = git remote get-url github 2>$null
if ($githubRemote) {
    Write-Host "   ? GitHub远程: $githubRemote" -ForegroundColor Green
    
    # 检查URL类型
    if ($githubRemote -like "*git@github.com*") {
        Write-Host "   ? 使用SSH方式" -ForegroundColor Cyan
    } elseif ($githubRemote -like "*https://github.com*") {
        Write-Host "   ? 使用HTTPS方式" -ForegroundColor Cyan
    }
} else {
    Write-Host "   ? 未配置GitHub远程仓库" -ForegroundColor Red
    Write-Host "   建议运行: git remote add github https://github.com/szqjl/yifeiAI-gd.git" -ForegroundColor Yellow
}
Write-Host ""

# 3. 测试GitHub连接
Write-Host "3. 测试GitHub连接..." -ForegroundColor Yellow
try {
    $result = git ls-remote github 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ? GitHub连接成功" -ForegroundColor Green
    } else {
        Write-Host "   ? GitHub连接失败" -ForegroundColor Red
        Write-Host "   错误信息: $result" -ForegroundColor Red
        Write-Host ""
        Write-Host "   可能的原因:" -ForegroundColor Yellow
        Write-Host "   1. 未配置Personal Access Token" -ForegroundColor Yellow
        Write-Host "   2. Token已过期或权限不足" -ForegroundColor Yellow
        Write-Host "   3. 网络连接问题" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   解决方案:" -ForegroundColor Yellow
        Write-Host "   1. 访问 https://github.com/settings/tokens 生成Token" -ForegroundColor Yellow
        Write-Host "   2. 确保Token有 'repo' 权限" -ForegroundColor Yellow
        Write-Host "   3. 推送时使用Token作为密码" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ? 测试失败: $_" -ForegroundColor Red
}
Write-Host ""

# 4. 检查SSH配置（如果使用SSH）
if ($githubRemote -like "*git@github.com*") {
    Write-Host "4. 检查SSH配置..." -ForegroundColor Yellow
    $sshTest = ssh -T git@github.com 2>&1
    if ($sshTest -like "*successfully authenticated*") {
        Write-Host "   ? SSH认证成功" -ForegroundColor Green
    } else {
        Write-Host "   ? SSH认证失败" -ForegroundColor Red
        Write-Host "   建议检查SSH密钥是否已添加到GitHub" -ForegroundColor Yellow
    }
    Write-Host ""
}

# 5. 总结
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "配置总结" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($credentialHelper -and $githubRemote) {
    Write-Host "? 基本配置已完成" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步操作:" -ForegroundColor Yellow
    Write-Host "1. 如果使用HTTPS，确保已生成Personal Access Token" -ForegroundColor White
    Write-Host "2. 运行推送命令: git push -u github main" -ForegroundColor White
    Write-Host "3. 首次推送时会提示输入用户名和Token" -ForegroundColor White
} else {
    Write-Host "??  需要完成基本配置" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "配置步骤:" -ForegroundColor Yellow
    Write-Host "1. 配置凭据助手: git config --global credential.helper manager-core" -ForegroundColor White
    Write-Host "2. 添加GitHub远程: git remote add github https://github.com/szqjl/yifeiAI-gd.git" -ForegroundColor White
    Write-Host "3. 生成Personal Access Token: https://github.com/settings/tokens" -ForegroundColor White
}

Write-Host ""
Write-Host "详细配置说明请参考: docs/GIT_SETUP_GUIDE.md" -ForegroundColor Cyan
Write-Host ""








