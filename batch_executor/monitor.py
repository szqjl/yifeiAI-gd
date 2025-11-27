"""
进程监控模块

用于监控服务器和客户端进程的状态。
"""

from typing import List


class ProcessMonitor:
    """监控服务器和客户端进程"""
    
    def is_running(self, process_name: str) -> bool:
        """检查进程是否运行"""
        pass
    
    def wait_for_termination(self, process_name: str, timeout: int) -> bool:
        """等待进程终止"""
        pass
    
    def kill_all(self, process_names: List[str]) -> None:
        """终止所有指定进程"""
        pass
