# 远程仓库设置指南

## 🎯 推荐的远程仓库名称

根据项目特点，建议使用以下名称之一：

### 1. **guandan-ai-client** ⭐ (推荐)
- **优点**: 简洁明了，符合项目功能
- **适用**: GitHub, Gitee, GitLab
- **示例**: `https://github.com/yourusername/guandan-ai-client.git`

### 2. **guandan-ai-client-njupt**
- **优点**: 包含平台信息，更具体
- **适用**: 需要明确标识平台来源时
- **示例**: `https://github.com/yourusername/guandan-ai-client-njupt.git`

### 3. **YiFeiAI-GD**
- **优点**: 使用当前目录名，保持一致性
- **适用**: 如果已有其他相关项目使用此命名规范
- **示例**: `https://github.com/yourusername/YiFeiAI-GD.git`

## 🚀 设置远程仓库步骤

### 方式一：GitHub

1. **在GitHub上创建仓库**
   - 访问 https://github.com/new
   - 仓库名称: `guandan-ai-client`
   - 描述: `南京邮电大学掼蛋AI算法对抗平台客户端`
   - 选择 Public 或 Private
   - **不要**初始化README、.gitignore或license（我们已经有了）

2. **添加远程仓库**
```bash
git remote add origin https://github.com/yourusername/guandan-ai-client.git
```

3. **推送代码**
```bash
# 推送main分支
git push -u origin main

# 推送develop分支
git push -u origin develop

# 推送所有分支
git push -u origin --all
```

### 方式二：Gitee（码云）

1. **在Gitee上创建仓库**
   - 访问 https://gitee.com/projects/new
   - 仓库名称: `guandan-ai-client`
   - 描述: `南京邮电大学掼蛋AI算法对抗平台客户端`
   - 选择 公开 或 私有

2. **添加远程仓库**
```bash
git remote add origin https://gitee.com/yourusername/guandan-ai-client.git
```

3. **推送代码**
```bash
git push -u origin main
git push -u origin develop
```

### 方式三：GitLab

1. **在GitLab上创建仓库**
   - 访问你的GitLab实例
   - 创建新项目
   - 项目名称: `guandan-ai-client`

2. **添加远程仓库**
```bash
git remote add origin https://gitlab.com/yourusername/guandan-ai-client.git
```

3. **推送代码**
```bash
git push -u origin main
git push -u origin develop
```

## 📋 完整的设置命令

```bash
# 1. 查看当前远程仓库（应该为空）
git remote -v

# 2. 添加远程仓库（选择一个平台）
# GitHub
git remote add origin https://github.com/yourusername/guandan-ai-client.git

# 或 Gitee
git remote add origin https://gitee.com/yourusername/guandan-ai-client.git

# 3. 验证远程仓库
git remote -v

# 4. 推送main分支
git push -u origin main

# 5. 推送develop分支
git checkout develop
git push -u origin develop

# 6. 推送所有分支和标签
git push -u origin --all
git push -u origin --tags

# 7. 设置默认分支（在远程仓库设置中）
# GitHub/Gitee: Settings -> Branches -> Default branch -> 选择 main
```

## 🔧 管理多个远程仓库

如果需要同时推送到多个远程仓库：

```bash
# 添加GitHub
git remote add github https://github.com/yourusername/guandan-ai-client.git

# 添加Gitee
git remote add gitee https://gitee.com/yourusername/guandan-ai-client.git

# 推送到GitHub
git push github main

# 推送到Gitee
git push gitee main

# 同时推送到两个仓库
git push github main && git push gitee main
```

## 📝 分支保护设置

### GitHub
1. 进入仓库 Settings -> Branches
2. 添加分支保护规则
3. 选择 `main` 分支
4. 启用以下选项：
   - ✅ Require a pull request before merging
   - ✅ Require approvals (至少1个)
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging

### Gitee
1. 进入仓库 设置 -> 分支保护
2. 添加保护规则
3. 选择 `main` 分支
4. 启用合并请求保护

## 🔐 SSH密钥配置（推荐）

使用SSH可以避免每次输入密码：

```bash
# 1. 生成SSH密钥（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. 查看公钥
cat ~/.ssh/id_ed25519.pub

# 3. 添加到GitHub/Gitee
# GitHub: Settings -> SSH and GPG keys -> New SSH key
# Gitee: 设置 -> SSH公钥 -> 添加公钥

# 4. 使用SSH URL添加远程仓库
git remote set-url origin git@github.com:yourusername/guandan-ai-client.git
# 或
git remote set-url origin git@gitee.com:yourusername/guandan-ai-client.git
```

## ✅ 验证设置

```bash
# 查看远程仓库
git remote -v

# 查看所有分支（包括远程）
git branch -a

# 拉取远程更新
git fetch origin

# 查看远程分支
git branch -r
```

## 🎯 推荐配置

### 仓库名称
**guandan-ai-client** (推荐)

### 仓库描述
```
南京邮电大学掼蛋AI算法对抗平台客户端 - 支持AI自动出牌决策、自我对弈、数据收集和平台信息监控
```

### 仓库标签
- `python`
- `ai`
- `guandan`
- `websocket`
- `game-ai`
- `njupt`

### README徽章（可选）
在README.md中添加：
```markdown
[![GitHub stars](https://img.shields.io/github/stars/yourusername/guandan-ai-client.svg)](https://github.com/yourusername/guandan-ai-client)
[![GitHub forks](https://img.shields.io/github/forks/yourusername/guandan-ai-client.svg)](https://github.com/yourusername/guandan-ai-client)
```

---

**提示**: 创建远程仓库后，记得更新README.md中的仓库链接！

