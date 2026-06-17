# Gitee仓库容量查看与扩容指南

## 📊 当前仓库状态

根据检查结果：
- **本地仓库总大小**: 2.3GB
- **Git对象大小**: 972MB
- **打包后大小**: 278.53 MB
- **大文件**: 多个模型文件（每个约14.5MB）和文档文件（最大70MB）

## 🔍 查看Gitee仓库容量

### 方法1：通过网页查看（推荐）

1. 访问仓库设置页面：
   ```
   https://gitee.com/Philsz/yifei-ai-gd/settings
   ```

2. 在左侧菜单中找到 **"仓库设置"** 或 **"仓库管理"**

3. 查看 **"仓库容量"** 或 **"存储使用情况"** 部分

### 方法2：通过API查看

```bash
# 需要Gitee访问令牌
curl -H "Authorization: token YOUR_GITEE_TOKEN" \
  https://gitee.com/api/v5/repos/Philsz/yifei-ai-gd
```

### 方法3：通过Git命令估算

```bash
# 查看推送大小
git count-objects -vH

# 查看远程仓库信息
git ls-remote --heads origin
```

## 📈 Gitee仓库容量限制

### 免费版限制
- **个人免费版**: 1GB 仓库容量
- **单文件限制**: 100MB
- **仓库数量**: 不限

### 付费版容量
- **个人版会员**: 根据套餐不同，容量更大
- **企业版**: 根据套餐提供更大容量

## 🚀 扩容方案

### 方案1：升级Gitee会员（最简单）

1. 访问 [Gitee会员中心](https://gitee.com/members)
2. 选择适合的会员套餐
3. 升级后自动获得更大容量

**优点**: 
- 操作简单
- 立即生效
- 无需修改代码

**缺点**: 
- 需要付费

### 方案2：使用Git LFS管理大文件（推荐）

Git LFS（Large File Storage）可以高效管理大文件，减少仓库体积。

#### 安装Git LFS

```bash
# Windows (使用Git for Windows自带)
git lfs install

# 或下载安装
# https://git-lfs.github.com/
```

#### 配置Git LFS

```bash
# 1. 初始化Git LFS
git lfs install

# 2. 追踪大文件类型
git lfs track "*.pth"           # 模型文件
git lfs track "*.pkl"           # pickle文件
git lfs track "*.h5"            # HDF5文件
git lfs track "*.docx"          # Word文档
git lfs track "*.pdf"           # PDF文档

# 3. 查看追踪规则
git lfs track

# 4. 提交.gitattributes文件
git add .gitattributes
git commit -m "配置Git LFS追踪大文件"
```

#### 迁移现有大文件到LFS

```bash
# 迁移所有匹配的文件
git lfs migrate import --include="*.pth,*.docx,*.pdf" --everything

# 强制推送（需要谨慎）
git push --force --all
git push --force --tags
```

**注意**: 迁移操作会重写历史，需要团队成员重新克隆仓库。

### 方案3：清理历史大文件

如果历史提交中包含大文件，可以清理历史记录。

#### 使用git filter-branch

```bash
# 删除指定文件的历史记录
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch models/*.pth" \
  --prune-empty --tag-name-filter cat -- --all

# 清理引用
git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

#### 使用BFG Repo-Cleaner（更快速）

```bash
# 下载BFG
# https://rtyley.github.io/bfg-repo-cleaner/

# 删除大文件
java -jar bfg.jar --strip-blobs-bigger-than 10M

# 清理
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**警告**: 清理历史会改变所有提交的SHA，需要强制推送，团队成员需要重新克隆。

### 方案4：使用外部存储

将大文件（如模型文件）存储在外部，仓库中只保留引用。

#### 选项A：使用云存储（OSS/COS）

```bash
# 示例：将模型文件上传到云存储
# 仓库中只保留下载脚本或配置文件
```

#### 选项B：使用Git子模块

```bash
# 将大文件目录作为独立仓库
git submodule add https://gitee.com/username/models.git models
```

## 📋 推荐实施方案

基于当前仓库情况，推荐以下组合方案：

### 短期方案（立即执行）

1. **查看当前容量使用情况**
   ```bash
   # 访问Gitee网页查看
   https://gitee.com/Philsz/yifei-ai-gd/settings
   ```

2. **清理不必要的模型文件**
   - 只保留最新或最重要的模型文件
   - 删除中间训练检查点（如epoch_10, epoch_20等）
   - 将旧模型移到外部存储

### 长期方案（推荐）

1. **配置Git LFS**
   ```bash
   git lfs install
   git lfs track "*.pth"
   git lfs track "*.docx"
   git lfs track "*.pdf"
   git add .gitattributes
   git commit -m "配置Git LFS"
   ```

2. **迁移大文件到LFS**
   ```bash
   git lfs migrate import --include="*.pth,*.docx,*.pdf" --everything
   ```

3. **推送到Gitee**
   ```bash
   git push origin --all --force
   ```

## ⚠️ 注意事项

1. **备份重要数据**: 在执行任何清理操作前，确保备份重要文件
2. **团队协作**: 如果多人协作，清理历史需要团队成员重新克隆
3. **Git LFS限制**: Gitee免费版Git LFS有流量限制
4. **测试环境**: 建议先在测试仓库中验证操作

## 🔗 相关链接

- [Gitee仓库管理文档](https://gitee.com/help/articles/4119)
- [Git LFS官方文档](https://git-lfs.github.com/)
- [Gitee会员中心](https://gitee.com/members)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

## 📝 操作记录

- **检查时间**: 2025-01-27
- **仓库大小**: 2.3GB (本地), 972MB (Git对象)
- **主要大文件**: 模型文件(.pth)和文档文件(.docx, .pdf)

