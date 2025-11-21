# 多远程仓库配置指南

## 📍 philsz 账户下的仓库

根据您提供的信息，philsz 账户下已有三个仓库。以下是配置多个远程仓库的方法。

## 🔧 配置多个远程仓库

### 方式一：为不同仓库设置不同的远程名称

```bash
# 主仓库（当前项目）
git remote add origin https://gitee.com/philsz/YiFeiAI-GD.git

# 其他仓库（示例）
git remote add repo2 https://gitee.com/philsz/仓库名2.git
git remote add repo3 https://gitee.com/philsz/仓库名3.git
```

### 方式二：使用不同的推送目标

```bash
# 推送到主仓库
git push origin main

# 推送到其他仓库
git push repo2 main
git push repo3 main
```

## 📋 查看所有远程仓库

```bash
# 查看所有远程仓库
git remote -v

# 查看特定远程仓库的详细信息
git remote show origin
```

## 🎯 当前项目配置

### 主远程仓库（YiFeiAI-GD）
- **远程名称**: origin
- **地址**: https://gitee.com/philsz/YiFeiAI-GD.git
- **用途**: 本项目的主要远程仓库

### 添加其他远程仓库

如果需要同时推送到其他仓库：

```bash
# 添加第二个远程仓库
git remote add backup https://gitee.com/philsz/其他仓库名.git

# 推送到多个仓库
git push origin main
git push backup main
```

## 📝 常用操作

### 推送到所有远程仓库

创建一个脚本或使用以下命令：

```bash
# 推送到origin
git push origin main
git push origin develop

# 推送到其他远程仓库（如果配置了）
git push backup main 2>/dev/null || echo "backup仓库未配置"
```

### 从特定远程拉取

```bash
# 从origin拉取
git pull origin main

# 从其他远程拉取
git pull backup main
```

### 更新远程仓库地址

```bash
# 更新origin地址
git remote set-url origin https://gitee.com/philsz/YiFeiAI-GD.git

# 添加新的远程仓库
git remote add <名称> <URL>

# 删除远程仓库
git remote remove <名称>
```

## 🔍 查看远程仓库信息

```bash
# 查看所有远程仓库
git remote -v

# 查看远程分支
git branch -r

# 查看远程仓库详细信息
git remote show origin
```

## ⚠️ 注意事项

1. **默认推送目标**: `git push` 默认推送到 `origin`
2. **分支同步**: 确保所有远程仓库的分支保持一致
3. **权限检查**: 确保有所有远程仓库的推送权限

## 📚 相关文档

- [REMOTE_REPO_INFO.md](../REMOTE_REPO_INFO.md) - 远程仓库详细信息
- [GIT_BRANCH_STRATEGY.md](GIT_BRANCH_STRATEGY.md) - 分支管理策略

---

**提示**: 如果您想将其他两个仓库的信息也添加到配置中，请告诉我仓库名称，我可以帮您更新配置。

