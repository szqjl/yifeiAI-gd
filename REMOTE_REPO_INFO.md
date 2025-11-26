# 远程仓库信息

## 📍 当前远程仓库配置

### 双重备份策略
项目采用 **Gitee + GitHub 双重备份** 策略，确保代码安全性和全球访问性。

### 主仓库信息（Gitee - YiFeiAI-GD）
- **平台**: Gitee（码云）
- **用户名**: Philsz（注意大小写）
- **仓库名称**: yifei-ai-gd
- **完整地址**: https://gitee.com/Philsz/yifei-ai-gd
- **远程名称**: origin
- **Git URL**: https://gitee.com/Philsz/yifei-ai-gd.git

### 备份仓库信息（GitHub - yifeiAI-gd）
- **平台**: GitHub
- **用户名**: szqjl
- **仓库名称**: yifeiAI-gd
- **完整地址**: https://github.com/szqjl/yifeiAI-gd
- **远程名称**: github
- **Git URL**: https://github.com/szqjl/yifeiAI-gd.git
- **SSH地址**: git@github.com:szqjl/yifeiAI-gd.git

### 仓库说明
- **Gitee (origin)**: 国内主仓库，访问速度快，CI/CD集成
- **GitHub (github)**: 国际备份仓库，全局协作，社区展示
如需配置多个远程仓库，请参考 [Git设置完整指南](docs/GIT_SETUP_GUIDE.md)

### Git 远程配置
```bash
# 查看远程仓库
git remote -v

# 输出（双重配置）：
# origin  https://gitee.com/Philsz/yifei-ai-gd.git (fetch)
# origin  https://gitee.com/Philsz/yifei-ai-gd.git (push)
# github git@github.com:szqjl/yifeiAI-gd.git (fetch)
# github git@github.com:szqjl/yifeiAI-gd.git (push)
```

### 添加GitHub远程仓库
```bash
# 添加GitHub为第二个远程仓库
git remote add github git@github.com:szqjl/yifeiAI-gd.git

# 验证配置
git remote -v

# 查看远程分支
git remote show origin
git remote show github
```

## 🚀 推送代码

### 双重推送策略
项目采用 **Gitee + GitHub 双重推送** 策略，确保代码在两个平台都有备份。

### 首次推送
```bash
# 推送到Gitee（主仓库）
git push -u origin main
git push -u origin develop
git push -u origin --all
git push -u origin --tags

# 推送到GitHub（备份仓库）
git push -u github main
git push -u github develop
git push -u github --all
git push -u github --tags
```

### 日常推送
```bash
# 双重推送当前分支
git push origin main && git push github main

# 推送到指定仓库
git push origin branch-name    # 推送到Gitee
git push github branch-name    # 推送到GitHub

# 拉取更新（通常从主仓库拉取）
git pull origin main
```

### 便捷脚本
创建推送脚本 `push_all.sh`：
```bash
#!/bin/bash
echo "推送代码到Gitee和GitHub..."

# 推送main分支
git push origin main
git push github main

# 推送develop分支（如果存在）
if git show-ref --verify --quiet refs/heads/develop; then
    git push origin develop
    git push github develop
fi

echo "双重推送完成！"
```

## 🔗 仓库链接

### Gitee仓库（主仓库）
- **Web访问**: https://gitee.com/Philsz/yifei-ai-gd
- **克隆地址**: https://gitee.com/Philsz/yifei-ai-gd.git
- **SSH地址**: git@gitee.com:Philsz/yifei-ai-gd.git

### GitHub仓库（备份仓库）
- **Web访问**: https://github.com/szqjl/yifeiAI-gd
- **克隆地址**: https://github.com/szqjl/yifeiAI-gd.git
- **SSH地址**: git@github.com:szqjl/yifeiAI-gd.git

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

## 🔐 SSH配置（推荐）

使用SSH可以避免每次输入密码，提高开发效率：

### SSH密钥生成
```bash
# 1. 生成SSH密钥（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. 查看公钥
cat ~/.ssh/id_ed25519.pub
```

### 添加到Gitee
```bash
# 访问: https://gitee.com/profile/sshkeys
# 点击"添加公钥"，粘贴公钥内容
```

### 添加到GitHub
```bash
# 访问: https://github.com/settings/keys
# 点击"New SSH key"，粘贴公钥内容
# 标题可以设置为 "YiFeiAI-GD"
```

### 配置SSH URL
```bash
# 设置Gitee使用SSH
git remote set-url origin git@gitee.com:Philsz/yifei-ai-gd.git

# 设置GitHub使用SSH
git remote set-url github git@github.com:szqjl/yifeiAI-gd.git
```

## ✅ 验证连接

```bash
# 测试Gitee连接
git ls-remote origin

# 测试GitHub连接
git ls-remote github

# 查看所有远程分支
git branch -r

# 获取所有远程更新
git fetch --all
```

## 🔧 故障排除

### SSH连接问题
```bash
# 测试SSH连接
ssh -T git@gitee.com
ssh -T git@github.com

# 如果失败，检查SSH配置
ssh -v git@gitee.com
ssh -v git@github.com
```

### 推送失败
```bash
# 检查远程配置
git remote -v

# 重新设置远程URL
git remote set-url origin https://gitee.com/Philsz/yifei-ai-gd.git
git remote set-url github https://github.com/szqjl/yifeiAI-gd.git

# 强制推送（注意：会覆盖远程历史）
git push -f origin main
git push -f github main
```

---

**最后更新**: 2025年11月24日

