#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文件清理脚本
安全地清理Git仓库中的大文件，包括从Git历史中删除
"""

import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

class LargeFileCleaner:
    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path)
        self.backup_dir = self.repo_path / "backup_large_files"
        self.large_files = []
        
    def find_large_files(self, min_size_mb=5):
        """查找大于指定大小的文件"""
        print(f"\n正在查找大于 {min_size_mb}MB 的文件...")
        cmd = [
            "git", "rev-list", "--objects", "--all"
        ]
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode != 0:
            print(f"错误: {result.stderr}")
            return []
        
        # 获取文件详细信息
        objects = result.stdout.strip().split('\n')
        large_files = []
        
        for obj_line in objects:
            if not obj_line.strip():
                continue
            parts = obj_line.split()
            if len(parts) < 2:
                continue
            
            obj_hash = parts[0]
            file_path = ' '.join(parts[1:])
            
            # 获取文件大小
            cmd = ["git", "cat-file", "-s", obj_hash]
            size_result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if size_result.returncode == 0:
                try:
                    size_bytes = int(size_result.stdout.strip())
                    size_mb = size_bytes / (1024 * 1024)
                    if size_mb >= min_size_mb:
                        large_files.append({
                            'path': file_path,
                            'size_mb': size_mb,
                            'hash': obj_hash
                        })
                except ValueError:
                    continue
        
        # 按大小排序
        large_files.sort(key=lambda x: x['size_mb'], reverse=True)
        self.large_files = large_files
        return large_files
    
    def print_large_files(self):
        """打印大文件列表"""
        if not self.large_files:
            print("没有找到大文件")
            return
        
        print(f"\n找到 {len(self.large_files)} 个大文件 (>5MB):")
        print("=" * 80)
        for i, file_info in enumerate(self.large_files, 1):
            print(f"{i:3d}. {file_info['size_mb']:7.2f} MB  {file_info['path']}")
        print("=" * 80)
        
        total_size = sum(f['size_mb'] for f in self.large_files)
        print(f"\n总大小: {total_size:.2f} MB")
    
    def backup_file(self, file_path):
        """备份文件到备份目录"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        source = self.repo_path / file_path
        if source.exists():
            dest = self.backup_dir / file_path.replace('/', '_')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            return str(dest)
        return None
    
    def remove_from_git_history(self, file_patterns):
        """从Git历史中删除文件"""
        print("\n⚠️  警告: 这将重写Git历史!")
        print("⚠️  操作后需要强制推送: git push --force --all")
        print("⚠️  团队成员需要重新克隆仓库")
        
        confirm = input("\n确认继续? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("操作已取消")
            return False
        
        # 使用git filter-branch删除文件
        for pattern in file_patterns:
            print(f"\n正在从Git历史中删除: {pattern}")
            cmd = [
                "git", "filter-branch", "--force", "--index-filter",
                f"git rm --cached --ignore-unmatch {pattern}",
                "--prune-empty", "--tag-name-filter", "cat", "--", "--all"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"警告: 删除 {pattern} 时出错: {result.stderr}")
            else:
                print(f"✓ 已删除: {pattern}")
        
        # 清理引用
        print("\n清理Git引用...")
        subprocess.run(["git", "for-each-ref", "--format=delete %(refname)", "refs/original"],
                      cwd=self.repo_path, capture_output=True)
        subprocess.run(["git", "reflog", "expire", "--expire=now", "--all"],
                      cwd=self.repo_path)
        subprocess.run(["git", "gc", "--prune=now", "--aggressive"],
                      cwd=self.repo_path)
        
        print("\n✓ Git历史清理完成")
        return True
    
    def remove_from_working_dir(self, file_paths):
        """从工作目录中删除文件（不删除Git历史）"""
        removed = []
        for file_path in file_paths:
            full_path = self.repo_path / file_path
            if full_path.exists():
                # 备份
                backup_path = self.backup_file(file_path)
                if backup_path:
                    print(f"已备份到: {backup_path}")
                
                # 删除文件
                full_path.unlink()
                removed.append(file_path)
                print(f"✓ 已删除: {file_path}")
        
        return removed
    
    def suggest_cleanup(self):
        """建议清理方案"""
        suggestions = {
            '模型中间检查点': [],
            '旧版本模型': [],
            '文档文件': [],
            '测试文件': []
        }
        
        for file_info in self.large_files:
            path = file_info['path']
            
            # 模型中间检查点
            if 'epoch_' in path and path.endswith('.pth'):
                epoch_match = None
                try:
                    import re
                    match = re.search(r'epoch_(\d+)', path)
                    if match:
                        epoch_num = int(match.group(1))
                        # 保留最后几个epoch，删除中间的
                        if epoch_num < 70:  # 保留epoch 70及以上
                            suggestions['模型中间检查点'].append(file_info)
                except:
                    pass
            
            # 文档文件
            if path.endswith(('.docx', '.pdf')) and 'skill' in path:
                suggestions['文档文件'].append(file_info)
            
            # 测试文件
            if 'Testscore' in path or 'test' in path.lower():
                suggestions['测试文件'].append(file_info)
        
        return suggestions


def main():
    cleaner = LargeFileCleaner()
    
    print("=" * 80)
    print("Git仓库大文件清理工具")
    print("=" * 80)
    
    # 查找大文件
    large_files = cleaner.find_large_files(min_size_mb=5)
    
    if not large_files:
        print("\n没有找到大于5MB的文件")
        return
    
    # 显示大文件列表
    cleaner.print_large_files()
    
    # 建议清理方案
    suggestions = cleaner.suggest_cleanup()
    
    print("\n" + "=" * 80)
    print("清理建议:")
    print("=" * 80)
    
    total_savings = 0
    for category, files in suggestions.items():
        if files:
            size = sum(f['size_mb'] for f in files)
            total_savings += size
            print(f"\n{category}: {len(files)} 个文件, 可节省 {size:.2f} MB")
            for f in files[:5]:  # 只显示前5个
                print(f"  - {f['size_mb']:.2f} MB  {f['path']}")
            if len(files) > 5:
                print(f"  ... 还有 {len(files) - 5} 个文件")
    
    print(f"\n总计可节省: {total_savings:.2f} MB")
    
    # 交互式选择
    print("\n" + "=" * 80)
    print("清理选项:")
    print("=" * 80)
    print("1. 清理模型中间检查点 (保留epoch 70+)")
    print("2. 清理文档文件 (docs/skill/)")
    print("3. 清理测试文件 (Testscore/)")
    print("4. 自定义清理")
    print("5. 仅从工作目录删除 (不删除Git历史)")
    print("6. 从Git历史中删除 (需要强制推送)")
    print("0. 退出")
    
    choice = input("\n请选择 (0-6): ").strip()
    
    files_to_remove = []
    
    if choice == '1':
        files_to_remove = [f['path'] for f in suggestions['模型中间检查点']]
    elif choice == '2':
        files_to_remove = [f['path'] for f in suggestions['文档文件']]
    elif choice == '3':
        files_to_remove = [f['path'] for f in suggestions['测试文件']]
    elif choice == '4':
        print("\n请输入要删除的文件路径（每行一个，空行结束）:")
        while True:
            path = input().strip()
            if not path:
                break
            files_to_remove.append(path)
    elif choice == '5':
        # 从工作目录删除
        all_suggested = []
        for files in suggestions.values():
            all_suggested.extend([f['path'] for f in files])
        files_to_remove = all_suggested
    
    if files_to_remove:
        print(f"\n将删除 {len(files_to_remove)} 个文件:")
        for f in files_to_remove[:10]:
            print(f"  - {f}")
        if len(files_to_remove) > 10:
            print(f"  ... 还有 {len(files_to_remove) - 10} 个文件")
        
        confirm = input("\n确认删除? (yes/no): ").strip().lower()
        if confirm == 'yes':
            if choice == '6':
                # 从Git历史删除
                cleaner.remove_from_git_history(files_to_remove)
            else:
                # 从工作目录删除
                removed = cleaner.remove_from_working_dir(files_to_remove)
                print(f"\n✓ 已删除 {len(removed)} 个文件")
                print("提示: 使用 'git add' 和 'git commit' 提交删除操作")
        else:
            print("操作已取消")
    elif choice == '0':
        print("退出")
    else:
        print("无效选择")


if __name__ == "__main__":
    main()

