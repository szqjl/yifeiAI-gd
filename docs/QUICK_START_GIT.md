# Git 仓库快速设置指南

## ✅ 当前状态

### 本地仓库
- ✅ Git仓库已初始化
- ✅ 主分支: `main`
- ✅ 开发分支: `develop`
- ✅ 初始提交已完成
- ✅ .gitignore 已配置

### 分支结构
```
main (主分支，用于生产环境)
  ↑
develop (开发分支，用于日常开发)
```

## 🚀 下一步：设置远程仓库

### 1. 选择远程仓库平台

推荐使用以下平台之一：
- **GitHub** (国际，适合开源项目)
- **Gitee** (国内，访问速度快)
- **GitLab** (自托管或云服务)

### 2. 推荐的仓库名称

**guandan-ai-client** ⭐ (推荐)

### 3. 创建远程仓库

#### GitHub
1. 访问 https://github.com/new
2. 仓库名称: `guandan-ai-client`
3. 描述: `南京邮电大学掼蛋AI算法对抗平台客户端`
4. 选择 Public 或 Private
5. **不要**初始化README、.gitignore或license

#### Gitee
1. 访问 https://gitee.com/projects/new
2. 仓库名称: `guandan-ai-client`
3. 描述: `南京邮电大学掼蛋AI算法对抗平台客户端`
4. 选择 公开 或 私有

### 4. 连接远程仓库

```bash
# 添加远程仓库（替换为你的用户名）
git remote add origin https://github.com/yourusername/guandan-ai-client.git

# 或使用Gitee
git remote add origin https://gitee.com/yourusername/guandan-ai-client.git

# 验证远程仓库
git remote -v
```

### 5. 推送代码

```bash
# 推送main分支
git push -u origin main

# 推送develop分支
git push -u origin develop

# 推送所有分支
git push -u origin --all
```

## 📋 完整命令示例

```bash
# 1. 添加远程仓库
git remote add origin https://github.com/yourusername/guandan-ai-client.git

# 2. 验证
git remote -v

# 3. 推送main分支
git push -u origin main

# 4. 推送develop分支
git checkout develop
git push -u origin develop

# 5. 返回main分支
git checkout main
```

## 📚 相关文档

- [Git分支管理策略](GIT_BRANCH_STRATEGY.md) - 详细的分支管理规范
- [远程仓库设置指南](../SETUP_REMOTE.md) - 完整的远程仓库配置说明

## 🔧 常用命令

### 查看分支
```bash
git branch          # 本地分支
git branch -a       # 所有分支（包括远程）
git branch -r       # 远程分支
```

### 切换分支
```bash
git checkout main       # 切换到main分支
git checkout develop    # 切换到develop分支
```

### 创建功能分支
```bash
# 从develop创建功能分支
git checkout develop
git checkout -b feature/websocket-client

# 开发完成后合并
git checkout develop
git merge feature/websocket-client
```

### 推送和拉取
```bash
git push origin branch-name    # 推送分支
git pull origin branch-name    # 拉取更新
git fetch origin              # 获取远程更新
```

## ⚠️ 注意事项

1. **首次推送前**
   - 确保已创建远程仓库
   - 检查远程仓库URL是否正确
   - 确认有推送权限

2. **分支保护**
   - 建议在远程仓库设置main分支保护
   - 要求Pull Request才能合并到main
   - 启用代码审查

3. **SSH密钥（推荐）**
   - 配置SSH密钥可以避免每次输入密码
   - 参考 [SETUP_REMOTE.md](../SETUP_REMOTE.md) 中的SSH配置

---

**提示**: 设置完成后，记得更新README.md中的仓库链接！

