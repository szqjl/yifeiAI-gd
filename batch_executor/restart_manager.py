"""
重启管理模块

管理服务器和客户端的重启，包括启动、等待和清理功能。
"""

import subprocess
import time
import logging
import os
from typing import List, Optional
from pathlib import Path

from .process_monitor import ProcessMonitor


logger = logging.getLogger(__name__)


class RestartManager:
    """管理服务器和客户端的重启"""
    
    def __init__(self, process_monitor: Optional[ProcessMonitor] = None):
        """
        初始化重启管理器
        
        Args:
            process_monitor: 进程监控器实例，如果未提供则创建新实例
        """
        self.process_monitor = process_monitor or ProcessMonitor()
        self.server_process: Optional[subprocess.Popen] = None
        self.client_processes: List[subprocess.Popen] = []
    
    def restart_server(
        self,
        server_path: str,
        game_count: int,
        max_retries: int = 3,
        wait_time: int = 15
    ) -> Optional[subprocess.Popen]:
        """
        重启服务器
        
        构建服务器启动命令，使用subprocess.Popen启动，
        等待服务器就绪，实现重试逻辑。
        
        Args:
            server_path: 服务器可执行文件路径
            game_count: 游戏场数
            max_retries: 最大重试次数，默认3次
            wait_time: 等待服务器就绪的时间（秒），默认15秒
            
        Returns:
            成功启动的服务器进程，如果失败返回None
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试启动服务器 (尝试 {attempt + 1}/{max_retries})")
                logger.info(f"服务器路径: {server_path}")
                logger.info(f"游戏场数: {game_count}")
                
                # 检查服务器文件是否存在
                if not os.path.exists(server_path):
                    logger.error(f"服务器文件不存在: {server_path}")
                    return None
                
                # 构建启动命令
                command = [server_path, str(game_count)]
                
                # 获取服务器所在目录作为工作目录
                server_dir = os.path.dirname(server_path) or "."
                logger.info(f"工作目录: {server_dir}")
                
                # 启动服务器进程
                # 不捕获输出，让服务器正常在新窗口中运行
                # 这样服务器才能正常输出并接受客户端连接
                process = subprocess.Popen(
                    command,
                    cwd=server_dir,  # 设置工作目录
                    creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, 'CREATE_NEW_CONSOLE') else 0
                )
                
                logger.info(f"服务器进程已启动，PID: {process.pid}")
                
                # 等待服务器就绪
                logger.info(f"等待服务器就绪 ({wait_time}秒)...")
                time.sleep(wait_time)
                
                # 检查进程是否仍在运行
                if process.poll() is None:
                    logger.info("✓ 服务器启动成功，进程正在运行")
                    self.server_process = process
                    return process
                else:
                    logger.warning(f"✗ 服务器进程意外终止，返回码: {process.returncode}")
                    
            except FileNotFoundError:
                logger.error(f"服务器可执行文件不存在: {server_path}")
                return None
            except PermissionError:
                logger.error(f"没有权限执行服务器: {server_path}")
                return None
            except Exception as e:
                logger.error(f"启动服务器时发生错误: {e}", exc_info=True)
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                logger.info("等待5秒后重试...")
                time.sleep(5)
        
        logger.error(f"服务器启动失败，已重试{max_retries}次")
        return None
    
    def restart_clients(
        self,
        client_scripts: List[str],
        wait_between: int = 3
    ) -> List[subprocess.Popen]:
        """
        重启所有客户端
        
        按顺序启动所有客户端，每个客户端之间等待指定时间。
        处理启动失败，继续启动其他客户端。
        
        Args:
            client_scripts: 客户端脚本路径列表
            wait_between: 每个客户端之间的等待时间（秒），默认3秒
            
        Returns:
            成功启动的客户端进程列表
        """
        processes = []
        
        for i, script_path in enumerate(client_scripts):
            try:
                logger.info(f"启动客户端 {i + 1}/{len(client_scripts)}: {script_path}")
                
                # 确定如何启动客户端（Python脚本）
                command = ['python', script_path]
                
                # 启动客户端进程
                # 不捕获输出，让输出显示在控制台窗口中
                process = subprocess.Popen(
                    command,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, 'CREATE_NEW_CONSOLE') else 0
                )
                
                logger.info(f"客户端 {i + 1} 已启动，PID: {process.pid}")
                processes.append(process)
                
                # 等待后再启动下一个客户端
                if i < len(client_scripts) - 1:
                    logger.info(f"等待{wait_between}秒后启动下一个客户端...")
                    time.sleep(wait_between)
                    
            except FileNotFoundError:
                logger.error(f"客户端脚本不存在: {script_path}")
                # 继续启动其他客户端
                continue
            except PermissionError:
                logger.error(f"没有权限执行客户端: {script_path}")
                # 继续启动其他客户端
                continue
            except Exception as e:
                logger.error(f"启动客户端时发生错误: {e}", exc_info=True)
                # 继续启动其他客户端
                continue
        
        self.client_processes = processes
        logger.info(f"成功启动 {len(processes)}/{len(client_scripts)} 个客户端")
        return processes
    
    def cleanup(self) -> None:
        """
        清理所有进程
        
        终止所有服务器和客户端进程，释放资源。
        """
        logger.info("开始清理所有进程...")
        
        # 终止所有客户端进程
        for i, process in enumerate(self.client_processes):
            try:
                if process.poll() is None:  # 进程仍在运行
                    logger.info(f"终止客户端进程 {i + 1}, PID: {process.pid}")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"客户端进程 {process.pid} 未响应终止信号，强制结束")
                        process.kill()
            except Exception as e:
                logger.error(f"终止客户端进程时发生错误: {e}")
        
        # 终止服务器进程
        if self.server_process is not None:
            try:
                if self.server_process.poll() is None:  # 进程仍在运行
                    logger.info(f"终止服务器进程, PID: {self.server_process.pid}")
                    self.server_process.terminate()
                    try:
                        self.server_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"服务器进程 {self.server_process.pid} 未响应终止信号，强制结束")
                        self.server_process.kill()
            except Exception as e:
                logger.error(f"终止服务器进程时发生错误: {e}")
        
        # 使用进程监控器确保服务器进程已终止
        # 注意：不要杀死所有python.exe进程，因为GUI本身也是Python进程
        process_names = ['guandan_offline_v1006.exe']
        self.process_monitor.kill_all(process_names)
        
        # 清空进程列表
        self.client_processes = []
        self.server_process = None
        
        logger.info("清理完成")
