#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 .rep 文件转换为 .xml 文件，以便在 Cursor 中编辑
用法: python scripts/tools/convert_rep_to_xml.py <rep_file_path>
"""

import sys
import os
import shutil
from pathlib import Path


def convert_rep_to_xml(rep_file_path: str, output_path: str = None):
    """
    将 .rep 文件转换为 .xml 文件（实际上只是重命名）
    
    Args:
        rep_file_path: .rep 文件路径
        output_path: 输出路径（可选，默认在同一目录下生成 .xml 文件）
    """
    rep_path = Path(rep_file_path)
    
    if not rep_path.exists():
        print(f"❌ 文件不存在: {rep_file_path}")
        return False
    
    if not rep_path.suffix.lower() == '.rep':
        print(f"⚠️ 文件扩展名不是 .rep: {rep_file_path}")
    
    # 确定输出路径
    if output_path is None:
        output_path = rep_path.with_suffix('.xml')
    else:
        output_path = Path(output_path)
    
    try:
        # 复制文件并重命名为 .xml
        shutil.copy2(rep_path, output_path)
        print(f"✅ 转换成功:")
        print(f"   源文件: {rep_path}")
        print(f"   目标文件: {output_path}")
        print(f"\n💡 提示: 现在可以在 Cursor 中打开 {output_path} 进行编辑")
        return True
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python scripts/tools/convert_rep_to_xml.py <rep_file_path> [output_path]")
        print("\n示例:")
        print('  python scripts/tools/convert_rep_to_xml.py "C:\\Program Files (x86)\\gdgame\\MobileGD\\replay\\szqjl_2024-02-04_12_20_23_\\_2024-02-04_12_15_56.rep"')
        print("\n或者批量转换:")
        print('  python scripts/tools/convert_rep_to_xml.py "C:\\Program Files (x86)\\gdgame\\MobileGD\\replay" --batch')
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    # 检查是否是批量转换模式
    if len(sys.argv) > 2 and sys.argv[2] == '--batch':
        # 批量转换目录中的所有 .rep 文件
        rep_dir = Path(input_path)
        if not rep_dir.is_dir():
            print(f"❌ 不是有效的目录: {input_path}")
            sys.exit(1)
        
        rep_files = list(rep_dir.rglob('*.rep'))
        if not rep_files:
            print(f"⚠️ 目录中没有找到 .rep 文件: {input_path}")
            sys.exit(0)
        
        print(f"📁 找到 {len(rep_files)} 个 .rep 文件")
        success_count = 0
        
        for rep_file in rep_files:
            print(f"\n处理: {rep_file}")
            if convert_rep_to_xml(str(rep_file)):
                success_count += 1
        
        print(f"\n✅ 批量转换完成: {success_count}/{len(rep_files)} 个文件转换成功")
    else:
        # 单个文件转换
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        convert_rep_to_xml(input_path, output_path)


if __name__ == '__main__':
    main()


