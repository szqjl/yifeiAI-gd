# OpenClaw 安装错误 128 解决方案

## 错误信息
```
npm ERR! code 128
```

## 错误原因

`npm ERR! code 128` 是 **Git 操作失败**的错误，通常发生在：
1. npm 安装包时，某些依赖来自 Git 仓库（GitHub/GitLab）
2. Git 无法访问远程仓库（网络、认证、SSL 问题）
3. 使用 npm 镜像源时，Git 依赖仍需要访问原始仓库

## 已完成的配置

✅ Git 已安装 (v2.51.0)
✅ Node.js 已安装 (v22.20.0)
✅ npm 已安装 (v9.8.1)
✅ 网络连接正常
✅ 已配置 Git 使用 HTTPS 协议
✅ 已增加 Git 缓冲区大小

## 解决方案

### 方案 1: 临时使用官方 npm 源（推荐）

某些包可能依赖 Git 仓库，使用官方源可能更稳定：

```powershell
# 临时使用官方源
npm install -g openclaw --registry https://registry.npmjs.org/

# 或者直接安装
npm install -g openclaw@latest
```

### 方案 2: 配置 Git 代理（如果使用代理）

```powershell
# 如果使用 HTTP 代理
git config --global http.proxy http://proxy.example.com:8080
git config --global https.proxy https://proxy.example.com:8080

# 如果使用 SOCKS 代理
git config --global http.proxy socks5://127.0.0.1:1080

# 取消代理
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### 方案 3: 禁用 Git SSL 验证（临时测试，不推荐生产环境）

```powershell
# 仅用于测试，不推荐长期使用
git config --global http.sslVerify false

# 安装完成后恢复
git config --global http.sslVerify true
```

### 方案 4: 手动安装 OpenClaw

```powershell
# 1. 先尝试直接安装
npm install -g openclaw@latest

# 2. 如果失败，查看详细错误
npm install -g openclaw@latest --loglevel verbose

# 3. 清理缓存后重试
npm cache clean --force
npm install -g openclaw@latest
```

### 方案 5: 检查具体失败的 Git 仓库

```powershell
# 查看详细错误信息
npm install -g openclaw@latest --loglevel verbose 2>&1 | Select-String "git"

# 或者查看 npm 日志
npm install -g openclaw@latest 2>&1 | Tee-Object -FilePath install.log
```

## 诊断步骤

### 1. 测试 Git 访问 GitHub

```powershell
# 测试 Git 克隆
git clone https://github.com/octocat/Hello-World.git test-repo
Remove-Item -Recurse -Force test-repo -ErrorAction SilentlyContinue
```

### 2. 检查 npm 日志

```powershell
# 查看 npm 配置
npm config list

# 查看详细安装日志
npm install -g openclaw@latest --loglevel verbose
```

### 3. 检查网络和防火墙

```powershell
# 测试 GitHub 连接
Test-NetConnection github.com -Port 443
Test-NetConnection gitlab.com -Port 443
```

## 推荐操作流程

1. **先尝试方案 1**（使用官方源）
   ```powershell
   npm install -g openclaw@latest --registry https://registry.npmjs.org/
   ```

2. **如果失败，查看详细错误**
   ```powershell
   npm install -g openclaw@latest --loglevel verbose
   ```

3. **根据错误信息调整**：
   - 如果是 SSL 问题 → 方案 3（临时）
   - 如果是网络问题 → 方案 2（配置代理）
   - 如果是特定仓库问题 → 方案 5（检查具体仓库）

## 常见问题

### Q: 为什么使用镜像源还会失败？
A: npm 镜像源只镜像 npm 包，但某些包的依赖可能来自 Git 仓库，这些需要直接访问原始仓库。

### Q: 如何知道是哪个 Git 仓库失败？
A: 使用 `--loglevel verbose` 查看详细日志，会显示具体的 Git URL。

### Q: 错误 128 和 403 有什么区别？
A: 
- 128: Git 操作失败（网络、认证、SSL）
- 403: 权限被拒绝（需要认证或仓库不存在）

## 相关资源

- [npm 错误代码文档](https://docs.npmjs.com/cli/v9/using-npm/scripts#npm-err-code-128)
- [Git 配置文档](https://git-scm.com/docs/git-config)
- [OpenClaw 官方文档](https://molt.bot/)

---

**创建时间**: 2026-01-18
**问题**: npm ERR! code 128 安装 OpenClaw 失败
