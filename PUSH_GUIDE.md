# 推送代码指南

## 📍 当前配置

- **远程仓库**: https://gitee.com/Philsz/YiFeiAI-GD.git
- **当前分支**: main
- **状态**: 等待推送

## 🚀 推送步骤

### 方法1: 使用HTTPS推送（需要输入用户名和密码）

```bash
# 推送main分支
git push -u origin main

# 推送develop分支
git push -u origin develop
```

**注意**: 如果提示404错误，可能的原因：
1. 仓库还未完全创建完成，请稍等片刻再试
2. 需要输入Gitee的用户名和密码
3. 仓库路径大小写问题（已更新为 Philsz）

### 方法2: 使用SSH推送（推荐，需要配置SSH密钥）

```bash
# 1. 配置SSH密钥（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. 查看公钥
cat ~/.ssh/id_ed25519.pub

# 3. 添加到Gitee
# 访问: https://gitee.com/profile/sshkeys
# 点击"添加公钥"，粘贴公钥内容

# 4. 更新远程URL为SSH方式
git remote set-url origin git@gitee.com:Philsz/YiFeiAI-GD.git

# 5. 测试SSH连接
ssh -T git@gitee.com

# 6. 推送代码
git push -u origin main
```

## 🔍 排查404错误

如果遇到404错误，请检查：

1. **确认仓库已创建**
   - 访问 https://gitee.com/Philsz/YiFeiAI-GD
   - 确认仓库存在且可访问

2. **检查仓库路径**
   ```bash
   git remote -v
   # 应该显示: https://gitee.com/Philsz/YiFeiAI-GD.git
   ```

3. **确认权限**
   - 确保有仓库的推送权限
   - 检查是否已登录Gitee账户

4. **等待仓库初始化**
   - 如果刚创建仓库，可能需要等待几秒钟

## ✅ 推送成功后的验证

```bash
# 查看远程分支
git branch -r

# 应该看到：
# origin/main
# origin/develop

# 查看远程仓库信息
git remote show origin
```

## 📝 推送所有分支

```bash
# 推送所有分支
git push -u origin --all

# 推送标签
git push -u origin --tags
```

## 🔗 相关文档

- [REMOTE_REPO_INFO.md](REMOTE_REPO_INFO.md) - 远程仓库详细信息
- [docs/PUSH_TROUBLESHOOTING.md](docs/PUSH_TROUBLESHOOTING.md) - 问题排查指南

---

**提示**: 如果持续遇到404错误，请：
1. 确认仓库在Gitee上已创建
2. 检查仓库路径是否正确（注意大小写：Philsz）
3. 尝试使用SSH方式推送

