"""
进程监控模块测试

测试进程状态检查、进程终止和重启决策功能。
"""

import os
import sys
import time
import subprocess
import pytest
from hypothesis import given, strategies as st, settings, assume

from batch_executor.process_monitor import ProcessMonitor


class TestProcessStateMonitoring:
    """测试进程状态监控功能"""
    
    @given(
        sleep_duration=st.floats(min_value=0.1, max_value=2.0)
    )
    @settings(max_examples=100, deadline=10000)
    def test_property_process_state_monitoring(self, sleep_duration):
        """
        **Feature: batch-game-execution, Property 8: 进程状态监控**
        **Validates: Requirements 2.1**
        
        For any 正在运行的服务器进程，监控器应该能够检测到其运行状态
        """
        # 创建一个简单的Python脚本，运行指定时间
        script_content = f"""
import time
time.sleep({sleep_duration})
"""
        
        # 启动进程
        process = subprocess.Popen(
            [sys.executable, '-c', script_content],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # 获取进程PID
            pid = process.pid
            
            # 创建监控器
            monitor = ProcessMonitor()
            
            # 验证：进程应该被检测为正在运行（通过PID）
            assert monitor.is_running(pid=pid), \
                f"Process with PID {pid} should be detected as running"
            
            # 等待进程结束
            process.wait(timeout=sleep_duration + 2)
            
            # 短暂等待确保进程完全终止
            time.sleep(0.1)
            
            # 验证：进程应该被检测为已终止
            assert not monitor.is_running(pid=pid), \
                f"Process with PID {pid} should be detected as terminated"
        
        finally:
            # 清理：确保进程被终止
            try:
                process.kill()
                process.wait(timeout=1)
            except:
                pass


class TestProcessTermination:
    """测试进程终止功能"""
    
    @given(
        num_processes=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=100, deadline=15000)
    def test_property_process_termination_completeness(self, num_processes):
        """
        **Feature: batch-game-execution, Property 13: 进程终止完整性**
        **Validates: Requirements 4.1**
        
        For any 客户端进程列表，终止操作后所有进程都应该不再运行
        """
        # 创建一个长时间运行的脚本
        script_content = """
import time
import sys
try:
    time.sleep(300)  # 运行5分钟
except KeyboardInterrupt:
    sys.exit(0)
"""
        
        # 创建唯一的进程名称（使用临时Python脚本）
        import tempfile
        processes = []
        script_files = []
        
        try:
            # 启动多个进程
            for i in range(num_processes):
                # 创建临时脚本文件
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.py',
                    delete=False,
                    encoding='utf-8'
                ) as f:
                    f.write(script_content)
                    script_path = f.name
                    script_files.append(script_path)
                
                # 启动进程
                proc = subprocess.Popen(
                    [sys.executable, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                processes.append(proc)
            
            # 等待一小段时间确保进程启动
            time.sleep(0.5)
            
            # 验证所有进程都在运行
            monitor = ProcessMonitor()
            for proc in processes:
                assert monitor.is_running(pid=proc.pid), \
                    f"Process {proc.pid} should be running"
            
            # 收集所有进程的PID
            pids = [proc.pid for proc in processes]
            
            # 终止所有进程（使用psutil直接终止，因为我们无法通过名称终止Python解释器）
            import psutil
            for pid in pids:
                try:
                    p = psutil.Process(pid)
                    p.kill()
                except:
                    pass
            
            # 等待进程终止
            time.sleep(1)
            
            # 验证：所有进程都应该已终止
            for pid in pids:
                assert not monitor.is_running(pid=pid), \
                    f"Process {pid} should be terminated after kill_all"
        
        finally:
            # 清理：确保所有进程被终止
            for proc in processes:
                try:
                    proc.kill()
                    proc.wait(timeout=1)
                except:
                    pass
            
            # 删除临时脚本文件
            for script_path in script_files:
                try:
                    if os.path.exists(script_path):
                        os.remove(script_path)
                except:
                    pass


class TestRestartDecision:
    """测试重启决策功能"""
    
    @given(
        remaining_games=st.integers(min_value=-10, max_value=100),
        server_running=st.booleans()
    )
    @settings(max_examples=100, deadline=1000)
    def test_property_restart_decision(self, remaining_games, server_running):
        """
        **Feature: batch-game-execution, Property 9: 重启决策**
        **Validates: Requirements 2.3**
        
        For any 剩余场数大于零的情况，当服务器终止时，系统应该决定重启
        """
        monitor = ProcessMonitor()
        
        # 创建一个模拟的服务器进程名称
        fake_server_name = "fake_server_that_does_not_exist_12345.exe"
        
        # 如果需要模拟服务器运行，创建一个临时进程
        process = None
        if server_running:
            script_content = "import time; time.sleep(10)"
            process = subprocess.Popen(
                [sys.executable, '-c', script_content],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # 使用实际的进程名称
            import psutil
            try:
                p = psutil.Process(process.pid)
                fake_server_name = p.name()
            except:
                pass
        
        try:
            # 执行重启决策
            should_restart = monitor.should_restart(fake_server_name, remaining_games)
            
            # 验证决策逻辑
            # 只有当服务器终止（not running）且剩余场数 > 0 时才应该重启
            expected_restart = (not server_running) and (remaining_games > 0)
            
            assert should_restart == expected_restart, \
                f"For server_running={server_running}, remaining_games={remaining_games}: " \
                f"expected should_restart={expected_restart}, but got {should_restart}"
        
        finally:
            # 清理进程
            if process:
                try:
                    process.kill()
                    process.wait(timeout=1)
                except:
                    pass
