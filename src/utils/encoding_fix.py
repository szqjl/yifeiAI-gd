# -*- coding: utf-8 -*-
"""
Windows控制台编码修复工具
统一处理Windows控制台UTF-8编码问题，解决中文乱码
"""
import sys
import io
import os


def fix_windows_console_encoding():
    """
    修复Windows控制台编码为UTF-8
    
    这个函数应该在所有脚本的最开始调用，确保中文输出正常显示。
    它会检查并修复sys.stdout和sys.stderr的编码。
    """
    if sys.platform != 'win32':
        return  # 非Windows系统不需要处理
    
    try:
        # 设置环境变量（如果可能）
        if hasattr(os, 'environ'):
            os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # 修复stdout编码
        if hasattr(sys.stdout, 'buffer'):
            # 如果已经是TextIOWrapper但编码不是utf-8，需要重新包装
            if isinstance(sys.stdout, io.TextIOWrapper):
                current_encoding = getattr(sys.stdout, 'encoding', None)
                if current_encoding and current_encoding.lower() not in ('utf-8', 'utf8'):
                    # 保存原始buffer，重新包装为UTF-8
                    try:
                        original_buffer = sys.stdout.buffer
                        sys.stdout = io.TextIOWrapper(
                            original_buffer, 
                            encoding='utf-8', 
                            errors='replace',
                            line_buffering=True
                        )
                    except (AttributeError, ValueError, OSError, TypeError):
                        pass
            else:
                # 如果不是TextIOWrapper，直接包装
                try:
                    sys.stdout = io.TextIOWrapper(
                        sys.stdout.buffer, 
                        encoding='utf-8', 
                        errors='replace',
                        line_buffering=True
                    )
                except (AttributeError, ValueError, OSError, TypeError):
                    pass
        
        # 修复stderr编码
        if hasattr(sys.stderr, 'buffer'):
            if isinstance(sys.stderr, io.TextIOWrapper):
                current_encoding = getattr(sys.stderr, 'encoding', None)
                if current_encoding and current_encoding.lower() not in ('utf-8', 'utf8'):
                    try:
                        original_buffer = sys.stderr.buffer
                        sys.stderr = io.TextIOWrapper(
                            original_buffer, 
                            encoding='utf-8', 
                            errors='replace',
                            line_buffering=True
                        )
                    except (AttributeError, ValueError, OSError, TypeError):
                        pass
            else:
                try:
                    sys.stderr = io.TextIOWrapper(
                        sys.stderr.buffer, 
                        encoding='utf-8', 
                        errors='replace',
                        line_buffering=True
                    )
                except (AttributeError, ValueError, OSError, TypeError):
                    pass
                    
    except (AttributeError, ValueError, OSError, TypeError) as e:
        # 如果设置失败，继续执行（可能是文件操作冲突或其他原因）
        # 不抛出异常，避免影响程序运行
        pass


# 自动执行（当模块被导入时）
fix_windows_console_encoding()

