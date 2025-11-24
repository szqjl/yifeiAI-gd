# 推送代码问题排查指南

## 🔍 常见问题

### 问题1: 404 not found

**错误信息**:
```
remote: [session-xxx] 404 not found!
fatal: repository 'https://gitee.com/philsz/YiFeiAI-GD.git/' not found
```

**可能原因**:
1. 仓库名称不正确
2. 仓库还未完全创建
3. 仓库路径大小写问题
4. 权限问题

**解决方法**:

#### 方法1: 确认仓库名称
```bash
# 检查远程URL是否正确
git remote -v

# 如果仓库名称不同，更新URL
git remote set-url origin https://gitee.com/philsz/实际仓库名.git
```

#### 方法2: 检查仓库是否创建
- 访问 https://gitee.com/philsz
- 查看仓库列表，确认仓库名称
- 确认仓库是否已创建完成

#### 方法3: 使用SSH方式（推荐）
```bash
# 如果已配置SSH密钥，使用SSH URL
git remote set-url origin git@gitee.com:philsz/YiFeiAI-GD.git

# 测试连接
ssh -T git@gitee.com
```

### 问题2: 权限被拒绝

**错误信息**:
```
Permission denied (publickey)
```

**解决方法**:
1. 配置SSH密钥
2. 或使用HTTPS方式，输入用户名和密码

### 问题3: 仓库为空

如果仓库刚创建，可能需要先推送：

```bash
# 推送main分支
git push -u origin main

# 如果提示需要先拉取，可以强制推送（谨慎使用）
git push -u origin main --force
```

## ✅ 正确的推送步骤

### 步骤1: 确认远程仓库URL
```bash
git remote -v
# 应该显示：
# origin  https://gitee.com/philsz/YiFeiAI-GD.git (fetch)
# origin  https://gitee.com/philsz/YiFeiAI-GD.git (push)
```

### 步骤2: 确认仓库已创建
- 访问 https://gitee.com/philsz/YiFeiAI-GD
- 确认仓库存在且可访问

### 步骤3: 推送代码
```bash
# 推送main分支
git push -u origin main

# 推送develop分支
git push -u origin develop
```

### 步骤4: 验证推送成功
```bash
# 查看远程分支
git branch -r

# 应该看到：
# origin/main
# origin/develop
```

## 🔧 如果仓库名称不同

如果实际创建的仓库名称不是 `YiFeiAI-GD`，需要更新远程URL：

```bash
# 更新为实际仓库名
git remote set-url origin https://gitee.com/philsz/实际仓库名.git

# 验证
git remote -v

# 推送
git push -u origin main
```

## 📝 检查清单

推送前确认：
- [ ] 远程仓库已在Gitee上创建
- [ ] 仓库名称正确（区分大小写）
- [ ] 远程URL配置正确
- [ ] 有仓库的推送权限
- [ ] 本地分支已准备好推送

## 🔗 相关文档

- [REMOTE_REPO_INFO.md](../REMOTE_REPO_INFO.md) - 远程仓库信息
- [GITEE_REPO_SETUP.md](GITEE_REPO_SETUP.md) - Gitee仓库创建指南

---

**提示**: 如果问题持续，请检查：
1. Gitee账户登录状态
2. 仓库的实际名称和路径
3. 网络连接状态

