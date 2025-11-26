#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一术语替换脚本
将知识库文档中的术语统一替换为标准术语
"""

import os
import re
from pathlib import Path

# 知识库目录
KNOWLEDGE_DIR = Path("docs/knowledge")

# 替换规则（按平台规则统一）
# 根据平台使用说明和江苏掼蛋规则：
# - "我方"：平台使用说明中的标准术语
# - "对家"：规则中的标准术语（位于对面的同伴）
# - "对方"：规则中的标准术语（上家和下家为对方）
REPLACEMENTS = [
    # 位置术语：统一为"上家"、"下家"（位置术语，保留）
    (r"上对方", "上家"),  # "上对方"替换为"上家"（上家是对手）
    (r"下对方", "下家"),  # "下对方"替换为"下家"（下家是对手）
    
    # 队友术语：统一为"对家"（平台规则标准术语）
    (r"搭档", "对家"),
    (r"同伴", "对家"),
    (r"队友", "对家"),
    
    # 对手术语：统一为"对方"（平台规则标准术语）
    # 注意：需要避免替换"敌方"中的"方"字，按顺序替换
    (r"敌方", "对方"),  # 先替换"敌方"
    (r"敌家", "对方"),  # "敌家"也替换为"对方"
    (r"敌人", "对方"),  # "敌人"替换为"对方"
    (r"制敌", "制对方"),  # "制敌"替换为"制对方"
    (r"封敌", "封对方"),  # "封敌"替换为"封对方"
    (r"判敌", "判对方"),  # "判敌"替换为"判对方"
    (r"敌对家", "对方对家"),  # "敌对家"替换为"对方对家"
    (r"下敌", "下对方"),  # "下敌"替换为"下对方"（下家是对手）
    (r"上敌", "上对方"),  # "上敌"替换为"上对方"（上家是对手）
    (r"控敌", "控对方"),  # "控敌"替换为"控对方"
    (r"敌枪", "对方枪"),  # "敌枪"替换为"对方枪"
    (r"敌开溜", "对方开溜"),  # "敌开溜"替换为"对方开溜"
    (r"比敌", "比对方"),  # "比敌"替换为"比对方"
    (r"炸敌", "炸对方"),  # "炸敌"替换为"炸对方"
    (r"被敌", "被对方"),  # "被敌"替换为"被对方"
    (r"敌打", "对方打"),  # "敌打"替换为"对方打"
    (r"敌尾", "对方尾"),  # "敌尾"替换为"对方尾"
    (r"骗敌", "骗对方"),  # "骗敌"替换为"骗对方"
    (r"等敌", "等对方"),  # "等敌"替换为"等对方"
    (r"防敌", "防对方"),  # "防敌"替换为"防对方"
    (r"敌出", "对方出"),  # "敌出"替换为"对方出"
    (r"敌两", "对方两"),  # "敌两"替换为"对方两"
    (r"敌既", "对方既"),  # "敌既"替换为"对方既"
    (r"敌看", "对方看"),  # "敌看"替换为"对方看"
    (r"敌犹豫", "对方犹豫"),  # "敌犹豫"替换为"对方犹豫"
    (r"敌首引", "对方首引"),  # "敌首引"替换为"对方首引"
    (r"敌首出", "对方首出"),  # "敌首出"替换为"对方首出"
    (r"压敌", "压对方"),  # "压敌"替换为"压对方"
    (r"恐敌", "恐对方"),  # "恐敌"替换为"恐对方"
    (r"敌不要", "对方不要"),  # "敌不要"替换为"对方不要"
    (r"逼敌", "逼对方"),  # "逼敌"替换为"逼对方"
    (r"敌剩", "对方剩"),  # "敌剩"替换为"对方剩"
    (r"敌拆", "对方拆"),  # "敌拆"替换为"对方拆"
    (r"敌封", "对方封"),  # "敌封"替换为"对方封"
    (r"敌改", "对方改"),  # "敌改"替换为"对方改"
    (r"敌有", "对方有"),  # "敌有"替换为"对方有"
    (r"敌能", "对方能"),  # "敌能"替换为"对方能"
    (r"敌下家", "对方下家"),  # "敌下家"替换为"对方下家"
    (r"判断敌", "判断对方"),  # "判断敌"替换为"判断对方"
    (r"敌要", "对方要"),  # "敌要"替换为"对方要"
    (r"发现敌", "发现对方"),  # "发现敌"替换为"发现对方"
    (r"遇敌", "遇对方"),  # "遇敌"替换为"遇对方"
    (r"牵敌", "牵对方"),  # "牵敌"替换为"牵对方"
    (r"敌\b", "对方"),    # 单独的"敌"字替换为"对方"（放在最后，避免误替换）
    # "对方"已经是标准术语，不需要替换
    
    # 己方术语：统一为"我方"（平台使用说明标准术语）
    # 注意：规则中使用"己方"，但平台使用说明中使用"我方"，按平台使用说明统一
    (r"己方", "我方"),  # 将"己方"统一为"我方"
]

# 需要保留的术语（不替换）
PRESERVE_TERMS = [
    "上家",
    "下家",
    "对家",  # 已经是标准术语
    "对手",  # 已经是标准术语
]

def should_preserve(text, match):
    """检查是否应该保留（不替换）"""
    for term in PRESERVE_TERMS:
        if term in text:
            return True
    return False

def replace_terms_in_file(file_path):
    """替换文件中的术语"""
    try:
        # 尝试UTF-8编码
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试GBK编码
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        original_content = content
        replacements_made = []
        
        # 应用替换规则
        for pattern, replacement in REPLACEMENTS:
            # 使用正则表达式替换
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                count = len(re.findall(pattern, content))
                replacements_made.append(f"  - {pattern} → {replacement}: {count}处")
                content = new_content
        
        # 如果有替换，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, replacements_made
        else:
            return False, []
    
    except Exception as e:
        print(f"错误：处理文件 {file_path} 时出错: {e}")
        return False, []

def main():
    """主函数"""
    # 获取所有Markdown文件
    md_files = list(KNOWLEDGE_DIR.rglob("*.md"))
    
    # 排除术语统一规范文件本身
    md_files = [f for f in md_files if f.name != "术语统一规范.md"]
    
    print(f"找到 {len(md_files)} 个Markdown文件")
    print("=" * 60)
    
    total_files_modified = 0
    total_replacements = 0
    
    for file_path in md_files:
        modified, replacements = replace_terms_in_file(file_path)
        if modified:
            total_files_modified += 1
            total_replacements += len(replacements)
            print(f"\n[OK] {file_path.relative_to(KNOWLEDGE_DIR)}")
            for r in replacements:
                print(r)
    
    print("\n" + "=" * 60)
    print(f"处理完成：")
    print(f"  - 修改文件数：{total_files_modified}")
    print(f"  - 总替换次数：{total_replacements}")
    print("\n[注意]")
    print("  1. '对方'已统一替换为'对手'，请检查是否需要改为'对手方'")
    print("  2. '上家'、'下家'已保留（位置术语）")
    print("  3. 请手动检查替换结果，确保语义正确")

if __name__ == "__main__":
    main()

