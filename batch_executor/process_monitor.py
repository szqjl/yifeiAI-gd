"""
进程监控模块

提供进程状态检查、进程终止和重启决策功能。
"""

import time
import subprocess
from typing import List, Optional
import psutil


class ProcessMonitor:
    """监控服务器和客户端进程"""
    
    def __init__(self, check_interval: int = 5):
        """
        初始化进程监控器
        
        Args:
            check_interval: 进程状态检查间隔（秒），默认5秒
        """
        self.check_interval = check_interval
    
    def is_running(self, process_name: Optional[str] = None, pid: Optional[int] = None) -> bool:
        """
        检查进程是否运行
        
        支持按进程名称或PID查询。至少需要提供一个参数。
        
        Args:
            process_name: 进程名称（例如 "guandan_offline_v1006.exe"）
            pid: 进程ID
            
        Returns:
            如果进程正在运行返回True，否则返回False
            
        Raises:
            ValueError: 如果process_name和pid都未提供
        """
        if process_name is None and pid is None:
            raise ValueError("必须提供process_name或pid参数")
        
        # 如果提供了PID，优先使用PID查询
        if pid is not None:
            try:
                process = psutil.Process(pid)
                # 检查进程是否存在且正在运行
                return process.is_running()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                return False
        
        # 使用进程名称查询
        if process_name is not None:
            try:
                for proc in psutil.process_iter(['name', 'pid']):
                    try:
                        # 比较进程名称（不区分大小写）
                        if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception:
                return False
        
        return False
    
    def wait_for_termination(self, process_name: str, timeout: int = 60) -> bool:
        """
        等待进程终止
        
        Args:
            process_name: 进程名称
            timeout: 超时时间（秒）
            
        Returns:
            如果进程在超时前终止返回True，否则返回False
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.is_running(process_name=process_name):
                return True
            time.sleep(self.check_interval)
        
        return False
    
    def kill_all(self, process_names: List[str]) -> None:
        """
        终止指定名称的所有进程
        
        使用 taskkill 命令（Windows）终止进程。
        验证进程已终止。
        
        Args:
            process_names: 要终止的进程名称列表
        """
        if not process_names:
            return
        
        for process_name in process_names:
            try:
                # 使用taskkill命令强制终止进程
                # /F: 强制终止
                # /IM: 按映像名称（进程名）
                # /T: 终止进程树（包括子进程）
                subprocess.run(
                    ['taskkill', '/F', '/IM', process_name, '/T'],
                    capture_output=True,
                    timeout=10
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                # 如果taskkill失败，尝试使用psutil
                try:
                    for proc in psutil.process_iter(['name', 'pid']):
                        try:
                            if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                                proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except Exception:
                    pass
        
        # 等待一小段时间确保进程终止
        time.sleep(1)
        
        # 验证所有进程已终止
        for process_name in process_names:
            # 如果进程仍在运行，再次尝试终止
            if self.is_running(process_name=process_name):
                try:
                    for proc in psutil.process_iter(['name', 'pid']):
                        try:
                            if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                                proc.kill()
                                proc.wait(timeout=3)
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                            continue
                except Exception:
                    pass
    
    def should_restart(self, server_process_name: str, remaining_games: int) -> bool:
        """
        重启决策逻辑
        
        检测服务器是否终止，并根据剩余场数决定是否重启。
        
        Args:
            server_process_name: 服务器进程名称
            remaining_games: 剩余游戏场数
            
        Returns:
            如果应该重启返回True，否则返回False
        """
        # 检查服务器是否已终止
        server_terminated = not self.is_running(process_name=server_process_name)
        
        # 只有当服务器终止且剩余场数大于零时才重启
        return server_terminated and remaining_games > 0
