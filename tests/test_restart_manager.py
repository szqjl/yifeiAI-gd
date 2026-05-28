"""
重启管理器测试

测试服务器和客户端的重启功能。
"""

import pytest
import subprocess
import time
import os
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st

from batch_executor.restart_manager import RestartManager
from batch_executor.process_monitor import ProcessMonitor


class TestRestartManager:
    """重启管理器单元测试"""
    
    def test_init(self):
        """测试初始化"""
        manager = RestartManager()
        assert manager.process_monitor is not None
        assert manager.server_process is None
        assert manager.client_processes == []
    
    def test_init_with_monitor(self):
        """测试使用自定义进程监控器初始化"""
        monitor = ProcessMonitor()
        manager = RestartManager(process_monitor=monitor)
        assert manager.process_monitor is monitor


class TestRestartServerProperty:
    """服务器重启属性测试"""
    
    @patch('subprocess.Popen')
    @patch('time.sleep')
    def test_restart_server_success(self, mock_sleep, mock_popen):
        """测试服务器成功启动"""
        # 模拟成功的进程
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 进程仍在运行
        mock_popen.return_value = mock_process
        
        manager = RestartManager()
        result = manager.restart_server("server.exe", 100)
        
        assert result is not None
        assert result == mock_process
        assert manager.server_process == mock_process
        mock_popen.assert_called_once()
    
    @patch('subprocess.Popen')
    @patch('time.sleep')
    def test_restart_server_retry_on_failure(self, mock_sleep, mock_popen):
        """测试服务器启动失败时的重试逻辑"""
        # 前两次失败，第三次成功
        mock_process_fail = Mock()
        mock_process_fail.pid = 12345
        mock_process_fail.poll.return_value = 1  # 进程已终止
        mock_process_fail.returncode = 1
        
        mock_process_success = Mock()
        mock_process_success.pid = 12346
        mock_process_success.poll.return_value = None  # 进程仍在运行
        
        mock_popen.side_effect = [mock_process_fail, mock_process_fail, mock_process_success]
        
        manager = RestartManager()
        result = manager.restart_server("server.exe", 100, max_retries=3)
        
        assert result is not None
        assert result == mock_process_success
        assert mock_popen.call_count == 3
    
    @patch('subprocess.Popen')
    @patch('time.sleep')
    def test_restart_server_max_retries_exceeded(self, mock_sleep, mock_popen):
        """测试超过最大重试次数"""
        # 所有尝试都失败
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 1  # 进程已终止
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        manager = RestartManager()
        result = manager.restart_server("server.exe", 100, max_retries=3)
        
        assert result is None
        assert mock_popen.call_count == 3


class TestRestartClientsProperty:
    """客户端重启属性测试"""
    
    @patch('subprocess.Popen')
    @patch('time.sleep')
    def test_restart_clients_success(self, mock_sleep, mock_popen):
        """测试客户端成功启动"""
        # 模拟成功的进程
        mock_processes = [Mock(pid=i) for i in range(1, 5)]
        mock_popen.side_effect = mock_processes
        
        manager = RestartManager()
        client_scripts = ['client1.py', 'client2.py', 'client3.py', 'client4.py']
        result = manager.restart_clients(client_scripts)
        
        assert len(result) == 4
        assert result == mock_processes
        assert manager.client_processes == mock_processes
        assert mock_popen.call_count == 4
    
    @patch('subprocess.Popen')
    @patch('time.sleep')
    def test_restart_clients_continue_on_failure(self, mock_sleep, mock_popen):
        """测试客户端启动失败时继续启动其他客户端"""
        # 第二个客户端启动失败
        mock_process1 = Mock(pid=1)
        mock_process3 = Mock(pid=3)
        mock_process4 = Mock(pid=4)
        
        mock_popen.side_effect = [
            mock_process1,
            FileNotFoundError("File not found"),
            mock_process3,
            mock_process4
        ]
        
        manager = RestartManager()
        client_scripts = ['client1.py', 'client2.py', 'client3.py', 'client4.py']
        result = manager.restart_clients(client_scripts)
        
        # 应该成功启动3个客户端（跳过第2个）
        assert len(result) == 3
        assert mock_process1 in result
        assert mock_process3 in result
        assert mock_process4 in result
        assert mock_popen.call_count == 4


class TestClientStartupOrderProperty:
    """
    **Feature: batch-game-execution, Property 14: 客户端启动顺序**
    **Validates: Requirements 4.4**
    
    For any 客户端脚本列表，启动顺序应该与列表顺序一致
    """
    
    @given(st.lists(st.text(min_size=1), min_size=1, max_size=10))
    def test_client_startup_order_property(self, client_scripts):
        """属性测试：客户端启动顺序"""
        with patch('subprocess.Popen') as mock_popen, patch('time.sleep'):
            # 为每个客户端创建模拟进程
            mock_processes = [Mock(pid=i) for i in range(len(client_scripts))]
            
            manager = RestartManager()
            
            # 记录调用顺序
            call_order = []
            
            def track_call(*args, **kwargs):
                # 从命令中提取脚本路径
                command = args[0]
                if len(command) >= 2:
                    script = command[1]
                    call_order.append(script)
                return mock_processes[len(call_order) - 1]
            
            mock_popen.side_effect = track_call
            
            # 启动客户端
            result = manager.restart_clients(client_scripts)
            
            # 验证启动顺序与输入列表顺序一致
            assert call_order == client_scripts
            
            # 验证所有客户端都被启动
            assert len(result) == len(client_scripts)


class TestErrorHandlingContinuityProperty:
    """
    **Feature: batch-game-execution, Property 15: 错误处理继续性**
    **Validates: Requirements 6.3**
    
    For any 客户端启动失败的情况，系统应该继续尝试启动其他客户端
    """
    
    @given(
        st.lists(st.text(min_size=1), min_size=2, max_size=10),
        st.integers(min_value=0, max_value=9)
    )
    def test_error_handling_continuity_property(
        self, client_scripts, fail_index
    ):
        """属性测试：错误处理继续性"""
        with patch('subprocess.Popen') as mock_popen, patch('time.sleep'):
            # 确保fail_index在有效范围内
            if fail_index >= len(client_scripts):
                fail_index = len(client_scripts) - 1
            
            # 创建模拟进程，其中一个失败
            mock_processes = []
            side_effects = []
            
            for i in range(len(client_scripts)):
                if i == fail_index:
                    # 这个客户端启动失败
                    side_effects.append(FileNotFoundError("File not found"))
                else:
                    # 其他客户端成功启动
                    mock_process = Mock(pid=i)
                    mock_processes.append(mock_process)
                    side_effects.append(mock_process)
            
            mock_popen.side_effect = side_effects
            
            manager = RestartManager()
            result = manager.restart_clients(client_scripts)
            
            # 验证：
            # 1. 应该尝试启动所有客户端
            assert mock_popen.call_count == len(client_scripts)
            
            # 2. 成功启动的客户端数量应该是总数减1
            assert len(result) == len(client_scripts) - 1
            
            # 3. 所有成功的进程都在结果中
            for process in mock_processes:
                assert process in result


class TestCleanupFunction:
    """清理功能测试"""
    
    @patch.object(ProcessMonitor, 'kill_all')
    def test_cleanup_terminates_all_processes(self, mock_kill_all):
        """测试清理功能终止所有进程"""
        manager = RestartManager()
        
        # 模拟一些运行中的进程
        mock_server = Mock()
        mock_server.poll.return_value = None  # 仍在运行
        mock_server.pid = 1000
        manager.server_process = mock_server
        
        mock_clients = [Mock(pid=i, poll=Mock(return_value=None)) for i in range(1, 5)]
        manager.client_processes = mock_clients
        
        # 执行清理
        manager.cleanup()
        
        # 验证所有进程都被终止
        mock_server.terminate.assert_called_once()
        for client in mock_clients:
            client.terminate.assert_called_once()
        
        # 验证进程监控器的kill_all被调用
        mock_kill_all.assert_called_once()
        
        # 验证进程列表被清空
        assert manager.server_process is None
        assert manager.client_processes == []
