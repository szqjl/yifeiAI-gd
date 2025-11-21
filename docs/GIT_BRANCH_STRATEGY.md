# Git 分支管理策略

## 📋 分支命名规范

### 主分支
- **main**: 主分支，用于生产环境，只接受来自develop的合并
- **develop**: 开发分支，用于日常开发，所有功能分支从此分支创建

### 功能分支
- **feature/功能名称**: 新功能开发
  - 示例: `feature/websocket-client`, `feature/info-monitor`
  - 命名规则: 小写字母，使用连字符分隔

### 修复分支
- **hotfix/修复描述**: 紧急修复
  - 示例: `hotfix/connection-timeout`, `hotfix/json-parsing-error`
  - 命名规则: 小写字母，使用连字符分隔

### 发布分支
- **release/版本号**: 发布准备
  - 示例: `release/v1.0.0`, `release/v1.1.0`
  - 命名规则: 使用版本号格式

## 🔄 分支工作流

```
main (生产环境)
  ↑
  | (合并)
develop (开发环境)
  ↑
  | (创建/合并)
feature/* (功能开发)
hotfix/* (紧急修复)
release/* (发布准备)
```

## 📝 分支使用指南

### 1. 创建功能分支
```bash
# 从develop分支创建新功能分支
git checkout develop
git pull origin develop
git checkout -b feature/websocket-client

# 开发完成后合并回develop
git checkout develop
git merge feature/websocket-client
git branch -d feature/websocket-client  # 删除本地分支
```

### 2. 创建修复分支
```bash
# 从main分支创建紧急修复分支
git checkout main
git pull origin main
git checkout -b hotfix/connection-timeout

# 修复完成后合并到main和develop
git checkout main
git merge hotfix/connection-timeout
git checkout develop
git merge hotfix/connection-timeout
git branch -d hotfix/connection-timeout
```

### 3. 创建发布分支
```bash
# 从develop分支创建发布分支
git checkout develop
git pull origin develop
git checkout -b release/v1.0.0

# 发布完成后合并到main和develop
git checkout main
git merge release/v1.0.0
git tag v1.0.0
git checkout develop
git merge release/v1.0.0
git branch -d release/v1.0.0
```

## 🚀 远程仓库设置

### 推荐的远程仓库名称

根据项目特点，建议使用以下名称之一：

1. **guandan-ai-client** (推荐)
   - 简洁明了
   - 符合项目功能
   - 易于记忆

2. **guandan-ai-client-njupt**
   - 包含平台信息
   - 更具体

3. **YiFeiAI-GD**
   - 使用当前目录名
   - 保持一致性

### 添加远程仓库

```bash
# GitHub示例
git remote add origin https://github.com/yourusername/guandan-ai-client.git

# Gitee示例
git remote add origin https://gitee.com/yourusername/guandan-ai-client.git

# 查看远程仓库
git remote -v

# 推送所有分支到远程
git push -u origin --all
git push -u origin --tags
```

## 📌 分支保护规则

### main分支
- ✅ 禁止直接推送
- ✅ 只能通过Pull Request合并
- ✅ 必须通过代码审查
- ✅ 必须通过所有测试

### develop分支
- ✅ 可以推送，但建议通过Pull Request
- ✅ 合并前需要代码审查
- ✅ 必须通过基础测试

## 🔧 常用命令

### 查看分支
```bash
# 查看本地分支
git branch

# 查看所有分支（包括远程）
git branch -a

# 查看远程分支
git branch -r
```

### 切换分支
```bash
# 切换到指定分支
git checkout branch-name

# 创建并切换到新分支
git checkout -b branch-name
```

### 推送分支
```bash
# 推送当前分支到远程
git push origin branch-name

# 推送所有分支
git push origin --all

# 设置上游分支
git push -u origin branch-name
```

### 删除分支
```bash
# 删除本地分支
git branch -d branch-name

# 强制删除本地分支
git branch -D branch-name

# 删除远程分支
git push origin --delete branch-name
```

## 📋 分支命名示例

### 功能分支
- `feature/websocket-communication`
- `feature/card-type-recognition`
- `feature/decision-engine`
- `feature/info-monitor`
- `feature/cooperation-strategy`

### 修复分支
- `hotfix/connection-timeout`
- `hotfix/json-parsing-error`
- `hotfix/memory-leak`
- `hotfix/state-sync-issue`

### 发布分支
- `release/v1.0.0`
- `release/v1.1.0`
- `release/v2.0.0`

## ⚠️ 注意事项

1. **提交信息规范**
   - 使用清晰的提交信息
   - 遵循约定式提交规范（可选）
   - 示例: `feat: 添加WebSocket通信模块`

2. **定期同步**
   - 开发前先拉取最新代码
   - 定期推送本地更改
   - 保持分支与远程同步

3. **代码审查**
   - 重要功能必须经过代码审查
   - 使用Pull Request进行合并
   - 确保代码质量

4. **分支清理**
   - 合并后及时删除已合并的分支
   - 定期清理过期的分支
   - 保持仓库整洁

---

**最后更新**: 2025年1月

