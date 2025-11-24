# 手动推送步骤

## 🔍 当前状态

- **远程URL**: https://gitee.com/Philsz/YiFeiAI-GD.git
- **本地分支**: main, develop
- **状态**: 等待推送

## ⚠️ 404错误排查

如果遇到404错误，请按以下步骤排查：

### 步骤1: 确认仓库存在

1. 在浏览器访问：https://gitee.com/Philsz/YiFeiAI-GD
2. 确认仓库页面可以正常打开
3. 查看仓库的"克隆/下载"按钮，确认实际的仓库地址

### 步骤2: 检查仓库路径

在Gitee仓库页面，点击"克隆/下载"按钮，查看显示的地址：
- 如果是 `https://gitee.com/Philsz/YiFeiAI-GD.git` - 路径正确
- 如果路径不同 - 需要更新远程URL

### 步骤3: 更新远程URL（如果需要）

如果实际路径不同，执行：
```bash
# 查看实际路径后更新
git remote set-url origin https://gitee.com/实际路径/YiFeiAI-GD.git
```

### 步骤4: 尝试推送

#### 方式A: HTTPS推送（需要输入用户名和密码）

```bash
git push -u origin main
```

如果提示输入用户名和密码：
- 用户名：您的Gitee用户名（可能是 Philsz 或 philsz）
- 密码：您的Gitee账户密码（或访问令牌）

#### 方式B: 使用访问令牌（推荐）

1. 在Gitee创建访问令牌：
   - 访问：https://gitee.com/profile/personal_access_tokens
   - 创建新令牌，勾选 `projects` 权限
   - 复制令牌

2. 推送时使用令牌作为密码：
```bash
git push -u origin main
# 用户名：Philsz（或您的用户名）
# 密码：粘贴访问令牌
```

#### 方式C: 使用SSH（最推荐）

1. 配置SSH密钥：
```bash
# 生成SSH密钥（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub
```

2. 添加到Gitee：
   - 访问：https://gitee.com/profile/sshkeys
   - 点击"添加公钥"
   - 粘贴公钥内容

3. 更新远程URL为SSH：
```bash
git remote set-url origin git@gitee.com:Philsz/YiFeiAI-GD.git
```

4. 测试连接：
```bash
ssh -T git@gitee.com
# 应该显示：Hi Philsz! You've successfully authenticated...
```

5. 推送：
```bash
git push -u origin main
```

## ✅ 推送成功后的操作

```bash
# 推送develop分支
git push -u origin develop

# 查看远程分支
git branch -r

# 应该看到：
# origin/main
# origin/develop
```

## 📝 如果仍然失败

请提供以下信息：
1. 在Gitee上访问仓库的实际URL
2. 仓库页面显示的克隆地址
3. 推送时的完整错误信息

---

**提示**: 如果仓库刚创建，可能需要等待几分钟让Gitee完成初始化。

