#!/bin/bash
# 自动清理大文件脚本
# 清理模型中间检查点、文档文件和测试文件

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 1

REPO_PATH="."
BACKUP_DIR="./backup_large_files_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="cleanup_log_$(date +%Y%m%d_%H%M%S).txt"

echo "=========================================="
echo "  自动清理大文件脚本"
echo "=========================================="
echo "备份目录: $BACKUP_DIR"
echo "日志文件: $LOG_FILE"
echo ""

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 记录日志
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "开始清理大文件..."

# 统计清理前的文件数量
BEFORE_COUNT=$(find models -name "*epoch_*.pth" -type f 2>/dev/null | wc -l)
BEFORE_SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')

log "清理前: $BEFORE_COUNT 个中间检查点文件, 仓库大小: $BEFORE_SIZE"

# 1. 清理模型中间检查点 (保留epoch 70及以上)
log "清理模型中间检查点 (epoch < 70)..."
CLEANED_MODELS=0
find models -name "*epoch_*.pth" -type f | while read file; do
    # 提取epoch数字
    epoch=$(echo "$file" | grep -oE "epoch_[0-9]+" | grep -oE "[0-9]+")
    if [ -n "$epoch" ] && [ "$epoch" -lt 70 ]; then
        # 备份
        mkdir -p "$BACKUP_DIR/$(dirname "$file")"
        cp "$file" "$BACKUP_DIR/$file" 2>/dev/null && log "备份: $file" || log "警告: 备份失败 $file"
        # 删除
        rm -f "$file" && log "删除: $file" && ((CLEANED_MODELS++)) || log "错误: 删除失败 $file"
    fi
done

# 2. 清理测试模型文件
log "清理测试模型文件..."
find models -name "*test*.pth" -type f | while read file; do
    mkdir -p "$BACKUP_DIR/$(dirname "$file")"
    cp "$file" "$BACKUP_DIR/$file" 2>/dev/null && log "备份: $file" || log "警告: 备份失败 $file"
    rm -f "$file" && log "删除: $file" || log "错误: 删除失败 $file"
done

find models -name "*quick*.pth" -type f | while read file; do
    mkdir -p "$BACKUP_DIR/$(dirname "$file")"
    cp "$file" "$BACKUP_DIR/$file" 2>/dev/null && log "备份: $file" || log "警告: 备份失败 $file"
    rm -f "$file" && log "删除: $file" || log "错误: 删除失败 $file"
done

# 3. 清理文档文件（已在.gitignore中，但需要从工作目录删除）
log "清理文档文件..."
find docs/skill -name "*.docx" -type f | while read file; do
    mkdir -p "$BACKUP_DIR/$(dirname "$file")"
    cp "$file" "$BACKUP_DIR/$file" 2>/dev/null && log "备份: $file" || log "警告: 备份失败 $file"
    rm -f "$file" && log "删除: $file" || log "错误: 删除失败 $file"
done

find docs/skill -name "*.pdf" -type f | while read file; do
    mkdir -p "$BACKUP_DIR/$(dirname "$file")"
    cp "$file" "$BACKUP_DIR/$file" 2>/dev/null && log "备份: $file" || log "警告: 备份失败 $file"
    rm -f "$file" && log "删除: $file" || log "错误: 删除失败 $file"
done

# 4. 清理Testscore目录（如果存在）
if [ -d "Testscore" ]; then
    log "清理Testscore目录..."
    mkdir -p "$BACKUP_DIR/Testscore"
    cp -r Testscore/* "$BACKUP_DIR/Testscore/" 2>/dev/null && log "备份Testscore目录" || log "警告: 备份Testscore失败"
    rm -rf Testscore/* && log "清理Testscore目录" || log "错误: 清理Testscore失败"
fi

# 统计清理后的文件数量
AFTER_COUNT=$(find models -name "*epoch_*.pth" -type f 2>/dev/null | wc -l)
AFTER_SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')

log "清理后: $AFTER_COUNT 个中间检查点文件, 仓库大小: $AFTER_SIZE"
log "清理完成！备份保存在: $BACKUP_DIR"

echo ""
echo "=========================================="
echo "  清理完成"
echo "=========================================="
echo "备份目录: $BACKUP_DIR"
echo "日志文件: $LOG_FILE"
echo ""
echo "下一步操作:"
echo "1. 检查备份目录确认文件已备份"
echo "2. 运行: git add -A"
echo "3. 运行: git commit -m '清理大文件: 删除中间检查点和文档文件'"
echo "4. 运行: git push origin main"
echo ""

