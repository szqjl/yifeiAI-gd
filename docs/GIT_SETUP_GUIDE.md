# Git 设置完整指南

## 📋 目录

1. [当前状态](#当前状态)
2. [创建远程仓库](#创建远程仓库)
3. [连接远程仓库](#连接远程仓库)
4. [推送代码](#推送代码)
5. [故障排查](#故障排查)
6. [常用命令](#常用命令)
7. [分支管理策略](#分支管理策略)

---

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

---

## 🚀 创建远程仓库

### 1. 选择远程仓库平台

推荐使用以下平台之一：
- **GitHub** (国际，适合开源项目)
- **Gitee** (国内，访问速度快) ⭐ 推荐
- **GitLab** (自托管或云服务)

### 2. 推荐的仓库名称

**guandan-ai-client** ⭐ (推荐)

或使用当前项目名称：**YiFeiAI-GD**

### 3. 在 Gitee 上创建仓库

#### 3.1 访问创建页面
- 地址：https://gitee.com/projects/new

#### 3.2 填写基本信息
- **仓库名称**: `YiFeiAI-GD` 或 `guandan-ai-client`
- **仓库介绍**: `南京邮电大学掼蛋AI算法对抗平台客户端 - 支持AI自动出牌决策、自我对弈、数据收集和平台信息监控`
- **仓库路径**: 自动生成
- **可见性**: 根据需求选择 **公开** 或 **私有**

#### 3.3 选择配置选项

| 选项 | 推荐值 | 说明 |
|------|--------|------|
| **语言** | Python | 项目使用 Python 开发 |
| **.gitignore** | 不选择 | 已有定制化的 .gitignore 文件 |
| **开源许可证** | MIT License | 与 README.md 中的声明一致 |
| **初始化README** | 不勾选 | 已有 README.md 文件 |

**重要提示**：
- ✅ **语言**: 选择 `Python`，有助于代码统计和语言分析
- ✅ **.gitignore**: 不选择（推荐），因为项目根目录已有定制化的 `.gitignore` 文件
- ✅ **开源许可证**: 选择 `MIT License`，与 README.md 中的声明一致
- ✅ **初始化README**: 不勾选，使用项目中的 README.md

#### 3.4 点击创建

### 4. 在 GitHub 上创建仓库（可选）

1. 访问 https://github.com/new
2. 仓库名称: `guandan-ai-client`
3. 描述: `南京邮电大学掼蛋AI算法对抗平台客户端`
4. 选择 Public 或 Private
5. **不要**初始化README、.gitignore或license

---

## 🔗 连接远程仓库

### 1. 添加远程仓库

```bash
# Gitee（推荐）
git remote add origin https://gitee.com/philsz/YiFeiAI-GD.git

# 或 GitHub
git remote add origin https://github.com/yourusername/guandan-ai-client.git
```

### 2. 验证远程仓库

```bash
# 查看远程仓库
git remote -v

# 应该显示：
# origin  https://gitee.com/philsz/YiFeiAI-GD.git (fetch)
# origin  https://gitee.com/philsz/YiFeiAI-GD.git (push)

# 测试连接
git ls-remote origin
```

### 3. 更新远程仓库地址

如果需要更改远程仓库地址：

```bash
# 查看当前远程地址
git remote -v

# 更新远程地址
git remote set-url origin https://gitee.com/philsz/YiFeiAI-GD.git

# 或使用SSH方式（推荐）
git remote set-url origin git@gitee.com:philsz/YiFeiAI-GD.git
```

---

## 📤 推送代码

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

### 验证推送成功

```bash
# 查看远程分支
git branch -r

# 应该看到：
# origin/main
# origin/develop

# 查看远程仓库详细信息
git remote show origin
```

---

## 🔍 故障排查

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
1. 配置SSH密钥（推荐）
2. 或使用HTTPS方式，输入用户名和密码

### 问题3: 仓库为空

如果仓库刚创建，可能需要先推送：

```bash
# 推送main分支
git push -u origin main

# 如果提示需要先拉取，可以强制推送（谨慎使用）
git push -u origin main --force
```

### 问题4: 仓库名称不同

如果实际创建的仓库名称不是 `YiFeiAI-GD`，需要更新远程URL：

```bash
# 更新为实际仓库名
git remote set-url origin https://gitee.com/philsz/实际仓库名.git

# 验证
git remote -v

# 推送
git push -u origin main
```

### 📝 推送前检查清单

推送前确认：
- [ ] 远程仓库已在Gitee/GitHub上创建
- [ ] 仓库名称正确（区分大小写）
- [ ] 远程URL配置正确
- [ ] 有仓库的推送权限
- [ ] 本地分支已准备好推送

---

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

### 删除分支
```bash
# 删除本地分支
git branch -d branch-name

# 强制删除本地分支
git branch -D branch-name

# 删除远程分支
git push origin --delete branch-name
```

---

## 🌿 分支管理策略

### 📋 分支命名规范

#### 主分支
- **main**: 主分支，用于生产环境，只接受来自develop的合并
- **develop**: 开发分支，用于日常开发，所有功能分支从此分支创建

#### 功能分支
- **feature/功能名称**: 新功能开发
  - 示例: `feature/websocket-client`, `feature/info-monitor`
  - 命名规则: 小写字母，使用连字符分隔

#### 修复分支
- **hotfix/修复描述**: 紧急修复
  - 示例: `hotfix/connection-timeout`, `hotfix/json-parsing-error`
  - 命名规则: 小写字母，使用连字符分隔

#### 发布分支
- **release/版本号**: 发布准备
  - 示例: `release/v1.0.0`, `release/v1.1.0`
  - 命名规则: 使用版本号格式

### 🔄 分支工作流

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

### 📝 分支使用指南

#### 1. 创建功能分支
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

#### 2. 创建修复分支
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

#### 3. 创建发布分支
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

### 📌 分支保护规则

#### main分支
- ✅ 禁止直接推送
- ✅ 只能通过Pull Request合并
- ✅ 必须通过代码审查
- ✅ 必须通过所有测试

#### develop分支
- ✅ 可以推送，但建议通过Pull Request
- ✅ 合并前需要代码审查
- ✅ 必须通过基础测试

### 📋 分支命名示例

#### 功能分支
- `feature/websocket-communication`
- `feature/card-type-recognition`
- `feature/decision-engine`
- `feature/info-monitor`
- `feature/cooperation-strategy`

#### 修复分支
- `hotfix/connection-timeout`
- `hotfix/json-parsing-error`
- `hotfix/memory-leak`
- `hotfix/state-sync-issue`

#### 发布分支
- `release/v1.0.0`
- `release/v1.1.0`
- `release/v2.0.0`

### ⚠️ 分支管理注意事项

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

## 📝 许可证说明

### MIT License 特点
- ✅ 允许商业使用
- ✅ 允许修改
- ✅ 允许分发
- ✅ 允许私人使用
- ✅ 需要包含许可证和版权声明
- ❌ 不提供任何担保

### 许可证文件位置
如果 Gitee/GitHub 自动生成了 LICENSE 文件，可以：
- 保留它（如果内容正确）
- 或者使用项目中的 LICENSE 文件（如果有）

---

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
   - 参考相关文档中的SSH配置

4. **.gitignore 冲突**
   - 如果选择了 Python .gitignore 模板
   - 需要检查是否与现有文件冲突
   - 建议使用现有的 .gitignore 文件

5. **README 冲突**
   - 不要勾选"初始化README"
   - 使用项目中的 README.md

6. **许可证一致性**
   - 确保远程仓库上的许可证与 README.md 中的声明一致
   - 都是 MIT License

---

## 🔗 相关文档

- [开发规范与规则](DEVELOPMENT_RULES.md) - 项目开发规范
- [阶段一任务清单](PHASE1_TASKS.md) - 开发任务指南

---

**提示**: 
- 设置完成后，记得更新README.md中的仓库链接！
- 如果问题持续，请检查：
  1. Gitee/GitHub账户登录状态
  2. 仓库的实际名称和路径
  3. 网络连接状态

