#!/bin/bash
# 大文件清理脚本（Shell版本）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 1

echo "=========================================="
echo "  Git仓库大文件清理工具"
echo "=========================================="
echo ""

REPO_PATH="."
BACKUP_DIR="./backup_large_files_$(date +%Y%m%d_%H%M%S)"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "【步骤1】查找大文件 (>5MB)"
echo "----------------------------------------"

# 查找大文件并保存到临时文件
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {size=$3; $1=$2=$3=""; print size " " $0}' | \
  awk '{if($1/1024/1024 > 5) printf "%.2f MB  %s\n", $1/1024/1024, substr($0, index($0,$2))}' | \
  sort -k1 -n -r > large_files_list.txt

cat large_files_list.txt | head -30

TOTAL_COUNT=$(wc -l < large_files_list.txt)
echo ""
echo "总计: $TOTAL_COUNT 个大文件"

echo ""
echo "【步骤2】清理建议"
echo "----------------------------------------"

# 统计各类文件
echo "模型中间检查点 (epoch < 70):"
grep -E "epoch_(1[0-9]|[2-6][0-9])\.pth" large_files_list.txt | wc -l | xargs echo "  数量:"

echo ""
echo "文档文件:"
grep -E "\.(docx|pdf)$" large_files_list.txt | wc -l | xargs echo "  数量:"

echo ""
echo "测试文件:"
grep -E "Testscore|test" large_files_list.txt | wc -l | xargs echo "  数量:"

echo ""
echo "【步骤3】选择清理方式"
echo "----------------------------------------"
echo "1. 清理模型中间检查点 (保留epoch 70+)"
echo "2. 清理文档文件"
echo "3. 清理测试文件"
echo "4. 清理所有建议的文件（仅工作目录）"
echo "5. 从Git历史中删除（危险操作）"
echo "0. 退出"

read -p "请选择 (0-5): " choice

case $choice in
  1)
    echo ""
    echo "将清理以下文件:"
    grep -E "epoch_(1[0-9]|[2-6][0-9])\.pth" large_files_list.txt | head -20
    read -p "确认删除? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
      grep -E "epoch_(1[0-9]|[2-6][0-9])\.pth" large_files_list.txt | \
        awk '{print $NF}' | \
        while read file; do
          if [ -f "$file" ]; then
            # 备份
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$file" "$BACKUP_DIR/$file" 2>/dev/null
            # 删除
            rm -f "$file"
            echo "✓ 已删除: $file"
          fi
        done
      echo ""
      echo "✓ 清理完成，备份保存在: $BACKUP_DIR"
      echo "提示: 使用 'git add' 和 'git commit' 提交删除操作"
    fi
    ;;
  2)
    echo ""
    echo "将清理以下文件:"
    grep -E "\.(docx|pdf)$" large_files_list.txt
    read -p "确认删除? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
      grep -E "\.(docx|pdf)$" large_files_list.txt | \
        awk '{print $NF}' | \
        while read file; do
          if [ -f "$file" ]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$file" "$BACKUP_DIR/$file" 2>/dev/null
            rm -f "$file"
            echo "✓ 已删除: $file"
          fi
        done
      echo ""
      echo "✓ 清理完成，备份保存在: $BACKUP_DIR"
    fi
    ;;
  3)
    echo ""
    echo "将清理以下文件:"
    grep -E "Testscore|test" large_files_list.txt
    read -p "确认删除? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
      grep -E "Testscore|test" large_files_list.txt | \
        awk '{print $NF}' | \
        while read file; do
          if [ -f "$file" ]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$file" "$BACKUP_DIR/$file" 2>/dev/null
            rm -f "$file"
            echo "✓ 已删除: $file"
          fi
        done
      echo ""
      echo "✓ 清理完成，备份保存在: $BACKUP_DIR"
    fi
    ;;
  4)
    echo ""
    echo "将清理所有建议的文件（仅从工作目录删除）:"
    echo "- 模型中间检查点 (epoch < 70)"
    echo "- 文档文件"
    echo "- 测试文件"
    read -p "确认删除? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
      # 清理模型中间检查点
      grep -E "epoch_(1[0-9]|[2-6][0-9])\.pth" large_files_list.txt | \
        awk '{print $NF}' | \
        while read file; do
          if [ -f "$file" ]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$file" "$BACKUP_DIR/$file" 2>/dev/null
            rm -f "$file"
            echo "✓ 已删除: $file"
          fi
        done
      
      # 清理文档文件
      grep -E "\.(docx|pdf)$" large_files_list.txt | \
        awk '{print $NF}' | \
        while read file; do
          if [ -f "$file" ]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$file" "$BACKUP_DIR/$file" 2>/dev/null
            rm -f "$file"
            echo "✓ 已删除: $file"
          fi
        done
      
      echo ""
      echo "✓ 清理完成，备份保存在: $BACKUP_DIR"
      echo "提示: 使用 'git add' 和 'git commit' 提交删除操作"
    fi
    ;;
  5)
    echo ""
    echo "⚠️  警告: 这将重写Git历史!"
    echo "⚠️  操作后需要强制推送: git push --force --all"
    echo "⚠️  团队成员需要重新克隆仓库"
    read -p "确认继续? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
      echo ""
      echo "请选择要从Git历史中删除的文件类型:"
      echo "1. 模型中间检查点"
      echo "2. 文档文件"
      echo "3. 测试文件"
      read -p "请选择 (1-3): " file_type
      
      case $file_type in
        1)
          PATTERN="models/*epoch_*[0-9].pth"
          ;;
        2)
          PATTERN="docs/archive/skill/*.{docx,pdf}"
          ;;
        3)
          PATTERN="Testscore/*"
          ;;
        *)
          echo "无效选择"
          exit 1
          ;;
      esac
      
      echo "正在从Git历史中删除: $PATTERN"
      git filter-branch --force --index-filter \
        "git rm --cached --ignore-unmatch $PATTERN" \
        --prune-empty --tag-name-filter cat -- --all
      
      # 清理引用
      git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin
      git reflog expire --expire=now --all
      git gc --prune=now --aggressive
      
      echo ""
      echo "✓ Git历史清理完成"
      echo "⚠️  请执行: git push --force --all"
    fi
    ;;
  0)
    echo "退出"
    ;;
  *)
    echo "无效选择"
    ;;
esac

# 清理临时文件
rm -f large_files_list.txt

