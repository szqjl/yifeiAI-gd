"""
测试BatchExecutor集成

测试主控制器的初始化和基本功能。
"""

import pytest
import tempfile
import os
from batch_executor.executor import BatchExecutor
from batch_executor.logging_config import setup_logging


class TestBatchExecutorIntegration:
    """测试BatchExecutor集成"""
    
    def test_batch_executor_initialization(self):
        """测试BatchExecutor可以正确初始化"""
        # 设置日志
        setup_logging(log_dir="logs")
        
        # 创建临时文件作为服务器路径
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as f:
            server_path = f.name
        
        try:
            # 创建BatchExecutor实例
            executor = BatchExecutor(
                target_games=12,
                server_path=server_path,
                client_scripts=['client1.py', 'client2.py'],
                diagnose_only=True
            )
            
            # 验证属性设置正确
            assert executor.target_games == 12
            assert executor.server_path == server_path
            assert len(executor.client_scripts) == 2
            assert executor.diagnose_only is True
            
            # 验证模块已初始化
            assert executor.diagnostic is not None
            assert executor.process_monitor is not None
            assert executor.tracker is not None
            assert executor.restart_manager is not None
            assert executor.validator is not None
            assert executor.signal_handler is not None
            
        finally:
            # 清理临时文件
            if os.path.exists(server_path):
                os.remove(server_path)
    
    def test_batch_executor_invalid_target_games(self):
        """测试BatchExecutor拒绝无效的目标场数"""
        # 设置日志
        setup_logging(log_dir="logs")
        
        # 创建临时文件作为服务器路径
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as f:
            server_path = f.name
        
        try:
            # 尝试创建BatchExecutor实例，应该抛出ValueError
            with pytest.raises(ValueError):
                BatchExecutor(
                    target_games=0,  # 无效的目标场数
                    server_path=server_path,
                    client_scripts=[]
                )
            
            with pytest.raises(ValueError):
                BatchExecutor(
                    target_games=-10,  # 无效的目标场数
                    server_path=server_path,
                    client_scripts=[]
                )
            
            with pytest.raises(ValueError):
                BatchExecutor(
                    target_games=10,  # 非 3 的倍数
                    server_path=server_path,
                    client_scripts=[]
                )
            
        finally:
            # 清理临时文件
            if os.path.exists(server_path):
                os.remove(server_path)
    
    def test_display_progress_method_exists(self):
        """测试display_progress方法存在且可调用"""
        # 设置日志
        setup_logging(log_dir="logs")
        
        # 创建临时文件作为服务器路径
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as f:
            server_path = f.name
        
        try:
            # 创建BatchExecutor实例
            executor = BatchExecutor(
                target_games=12,
                server_path=server_path,
                client_scripts=[],
                diagnose_only=True
            )
            
            # 验证display_progress方法存在
            assert hasattr(executor, 'display_progress')
            assert callable(executor.display_progress)
            
        finally:
            # 清理临时文件
            if os.path.exists(server_path):
                os.remove(server_path)
