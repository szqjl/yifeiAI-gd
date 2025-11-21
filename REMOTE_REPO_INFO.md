# 远程仓库信息

## 📍 当前远程仓库配置

### 主仓库信息（YiFeiAI-GD）
- **平台**: Gitee（码云）
- **用户名**: Philsz（注意大小写）
- **仓库名称**: yifei-ai-gd
- **完整地址**: https://gitee.com/Philsz/yifei-ai-gd
- **远程名称**: origin
- **Git URL**: https://gitee.com/Philsz/yifei-ai-gd.git

### philsz 账户下的仓库
根据您提供的信息，philsz 账户下已有三个仓库。当前项目使用 **YiFeiAI-GD** 作为主远程仓库。

如需配置其他仓库，请参考 [多远程仓库配置指南](docs/MULTI_REPO_SETUP.md)

### Git 远程配置
```bash
# 查看远程仓库
git remote -v

# 输出：
# origin  https://gitee.com/Philsz/yifei-ai-gd.git (fetch)
# origin  https://gitee.com/Philsz/yifei-ai-gd.git (push)
```

## 🚀 推送代码

### 首次推送
```bash
# 推送main分支
git push -u origin main

# 推送develop分支
git push -u origin develop

# 推送所有分支
git push -u origin --all

# 推送标签
git push -u origin --tags
```

### 日常推送
```bash
# 推送当前分支
git push

# 推送指定分支
git push origin branch-name

# 拉取更新
git pull origin main
```

## 🔗 仓库链接

- **Web访问**: https://gitee.com/Philsz/yifei-ai-gd
- **克隆地址**: https://gitee.com/Philsz/yifei-ai-gd.git
- **SSH地址**: git@gitee.com:Philsz/yifei-ai-gd.git

## 📋 分支信息

### 主分支
- **main**: 生产环境分支
- **develop**: 开发环境分支

### 推送分支到远程
```bash
# 推送main分支
git checkout main
git push -u origin main

# 推送develop分支
git checkout develop
git push -u origin develop
```

## ⚙️ 更新远程地址

如果需要更改远程仓库地址：

```bash
# 查看当前远程地址
git remote -v

# 更新远程地址
git remote set-url origin https://gitee.com/Philsz/yifei-ai-gd.git

# 或使用SSH
git remote set-url origin git@gitee.com:Philsz/yifei-ai-gd.git
```

## 🔐 SSH配置（可选）

使用SSH可以避免每次输入密码：

```bash
# 1. 生成SSH密钥（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. 查看公钥
cat ~/.ssh/id_ed25519.pub

# 3. 添加到Gitee
# 访问: https://gitee.com/profile/sshkeys
# 点击"添加公钥"，粘贴公钥内容

# 4. 使用SSH URL
git remote set-url origin git@gitee.com:philsz/YiFeiAI-GD.git
```

## ✅ 验证连接

```bash
# 测试连接
git ls-remote origin

# 查看远程分支
git branch -r

# 获取远程更新
git fetch origin
```

---

**最后更新**: 2025年1月

