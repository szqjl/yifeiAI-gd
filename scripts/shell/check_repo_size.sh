#!/bin/bash
# Gitee仓库容量检查脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 1

echo "=========================================="
echo "  仓库容量检查报告"
echo "=========================================="
echo ""

# 1. 检查本地仓库大小
echo "【本地仓库大小】"
echo "----------------------------------------"
du -sh . 2>/dev/null | awk '{print "总大小: " $1}'
du -sh .git 2>/dev/null | awk '{print "Git对象: " $1}'
echo ""

# 2. Git对象统计
echo "【Git对象统计】"
echo "----------------------------------------"
git count-objects -vH 2>/dev/null | grep -E "count|size|size-pack" || echo "无法获取Git统计信息"
echo ""

# 3. 查找大文件（前10个）
echo "【仓库中大文件（Top 10）】"
echo "----------------------------------------"
git rev-list --objects --all 2>/dev/null | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' 2>/dev/null | \
  awk '/^blob/ {size=$3; $1=$2=$3=""; print size " " $0}' | \
  sort -k1 -n -r | \
  head -10 | \
  awk '{printf "%.2f MB  %s\n", $1/1024/1024, substr($0, index($0,$2))}'
echo ""

# 4. 检查远程仓库信息
echo "【远程仓库信息】"
echo "----------------------------------------"
git remote -v 2>/dev/null
echo ""

# 5. 检查是否有大文件需要Git LFS
echo "【建议】"
echo "----------------------------------------"
echo "1. 查看Gitee仓库容量："
echo "   访问 https://gitee.com/Philsz/yifei-ai-gd/settings"
echo "   在'仓库设置'中查看'仓库容量'"
echo ""
echo "2. Gitee免费仓库容量："
echo "   - 个人免费版：1GB"
echo "   - 企业版：根据套餐不同"
echo ""
echo "3. 扩容方式："
echo "   a) 升级Gitee会员（个人版/企业版）"
echo "   b) 清理历史大文件（使用git filter-branch或BFG）"
echo "   c) 使用Git LFS管理大文件（模型文件、文档等）"
echo ""
echo "4. 当前仓库大文件建议："
echo "   - 模型文件(.pth)建议使用Git LFS"
echo "   - 大文档文件(.docx, .pdf)可考虑移到外部存储"
echo ""

