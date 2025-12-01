# -*- coding: utf-8 -*-
"""
知识库依赖检查工具

检查知识库功能所需的依赖是否已安装，并提供清晰的错误提示。
"""

import sys
from typing import Tuple, Dict


def check_yaml_dependency() -> Tuple[bool, str, str]:
    """
    检查yaml模块是否可用
    
    Returns:
        (is_available, version, error_message)
        - is_available: yaml模块是否可用
        - version: yaml版本（如果可用）
        - error_message: 错误信息（如果不可用）
    """
    try:
        import yaml
        version = getattr(yaml, '__version__', 'unknown')
        return True, version, ""
    except ImportError:
        error_msg = (
            "❌ PyYAML模块未安装！\n"
            "   知识库功能将受限：\n"
            "   - ✅ 5条内置规则可用\n"
            "   - ❌ 29条动态规则无法加载\n"
            "   - ⚠️  Markdown元数据解析受限\n"
            "\n"
            "   安装方法：\n"
            "   pip install pyyaml\n"
            "   或：\n"
            "   pip install -r requirements.txt\n"
        )
        return False, "", error_msg


def check_knowledge_dependencies() -> Dict[str, Tuple[bool, str, str]]:
    """
    检查所有知识库依赖
    
    Returns:
        字典，键为依赖名称，值为(is_available, version, error_message)
    """
    results = {}
    
    # 检查yaml
    results['yaml'] = check_yaml_dependency()
    
    return results


def print_dependency_status(verbose: bool = True):
    """
    打印依赖状态
    
    Args:
        verbose: 是否显示详细信息
    """
    results = check_knowledge_dependencies()
    
    print("=" * 60)
    print("知识库依赖检查")
    print("=" * 60)
    
    all_ok = True
    for dep_name, (is_available, version, error_msg) in results.items():
        if is_available:
            status = "✅"
            info = f"已安装 (版本: {version})"
        else:
            status = "❌"
            info = "未安装"
            all_ok = False
        
        print(f"{status} {dep_name}: {info}")
        
        if not is_available and verbose:
            print(f"\n{error_msg}")
    
    print("=" * 60)
    
    if all_ok:
        print("✅ 所有依赖已安装，知识库功能完整可用")
    else:
        print("⚠️  部分依赖缺失，知识库功能将受限")
        print("   建议运行: pip install -r requirements.txt")
    
    print("=" * 60)
    
    return all_ok


if __name__ == "__main__":
    # 命令行直接运行时进行检查
    print_dependency_status()

