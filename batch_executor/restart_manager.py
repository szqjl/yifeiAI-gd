"""
重启管理模块

管理服务器和客户端的重启，包括启动、等待和清理功能。
"""

import subprocess
import sys
import time
import logging
import os
from typing import List, Optional
from pathlib import Path

from .process_monitor import ProcessMonitor


logger = logging.getLogger(__name__)


class RestartManager:
    """管理服务器和客户端的重启"""
    
    def __init__(self, process_monitor: Optional[ProcessMonitor] = None, project_root: Optional[Path] = None):
        """
        初始化重启管理器
        
        Args:
            process_monitor: 进程监控器实例，如果未提供则创建新实例
            project_root: 项目根目录（用于路径解析）
        """
        self.process_monitor = process_monitor or ProcessMonitor()
        self.server_process: Optional[subprocess.Popen] = None
        self.client_processes: List[subprocess.Popen] = []
        # 如果没有提供项目根目录，使用默认值（batch_executor的父目录）
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = project_root
    
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
                # 捕获输出以便读取战绩，但不阻塞
                process = subprocess.Popen(
                    command,
                    cwd=server_dir,  # 设置工作目录
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                    text=True,
                    bufsize=1  # 行缓冲
                )
                
                logger.info(f"服务器进程已启动，PID: {process.pid}")
                
                # 等待服务器就绪
                logger.info(f"等待服务器就绪 ({wait_time}秒)...")
                
                # 分阶段等待，每2秒检查一次进程状态
                check_interval = 2
                elapsed = 0
                server_output_lines = []
                
                while elapsed < wait_time:
                    time.sleep(min(check_interval, wait_time - elapsed))
                    elapsed += check_interval
                    
                    # 检查进程状态
                    return_code = process.poll()
                    if return_code is not None:
                        # 进程已退出，尝试读取输出
                        logger.warning(f"服务器进程在 {elapsed} 秒后退出，返回码: {return_code}")
                        try:
                            if process.stdout:
                                # 读取剩余输出
                                remaining = process.stdout.read()
                                if remaining:
                                    server_output_lines = remaining.splitlines()
                        except:
                            pass
                        break
                
                # 输出服务器日志（如果有）
                if server_output_lines:
                    logger.info("服务器输出（最后10行）:")
                    for line in server_output_lines[-10:]:
                        logger.info(f"  {line}")
                
                # 最终检查进程是否仍在运行
                if process.poll() is None:
                    logger.info("✓ 服务器启动成功，进程正在运行")
                    self.server_process = process
                    return process
                else:
                    return_code = process.returncode
                    logger.error(f"✗ 服务器进程已终止，返回码: {return_code}")
                    if server_output_lines:
                        logger.error("服务器错误输出:")
                        for line in server_output_lines[-5:]:
                            logger.error(f"  {line}")
                    else:
                        logger.error("提示: 服务器可能启动失败，请检查服务器路径和参数是否正确")
                    
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
                script_path = script_path.strip()  # 去除前后空格
                
                # 将相对路径转换为绝对路径
                if not os.path.isabs(script_path):
                    # 如果是相对路径，先尝试相对于当前工作目录
                    abs_script_path = os.path.abspath(script_path)
                    
                    # 如果当前工作目录下的路径不存在，尝试相对于项目根目录
                    if not os.path.exists(abs_script_path):
                        abs_script_path = self.project_root / script_path
                        abs_script_path = str(abs_script_path.resolve())
                else:
                    abs_script_path = script_path
                
                # 验证文件是否存在
                if not os.path.exists(abs_script_path):
                    logger.error(f"客户端脚本不存在: {script_path}")
                    logger.error(f"  尝试的绝对路径: {abs_script_path}")
                    logger.error(f"  当前工作目录: {os.getcwd()}")
                    logger.error(f"  项目根目录: {self.project_root}")
                    continue
                
                logger.info(f"启动客户端 {i + 1}/{len(client_scripts)}: {script_path}")
                logger.info(f"  绝对路径: {abs_script_path}")
                
                # 确定如何启动客户端（Python脚本）
                command = ['python', abs_script_path]
                
                # 启动客户端进程
                # 不捕获输出，让输出显示在控制台窗口中
                # Windows上使用start命令创建新窗口，其他平台使用默认方式
                if sys.platform == 'win32':
                    # Windows: 使用start命令创建新的控制台窗口显示客户端输出
                    # start命令会打开新窗口并执行命令
                    # 使用start命令在新窗口中启动，窗口标题包含脚本名便于识别
                    window_title = f"客户端{i+1}: {os.path.basename(abs_script_path)}"
                    # 确保工作目录是项目根目录，这样相对导入才能正常工作
                    work_dir = str(self.project_root.resolve())
                    # 计算相对于项目根目录的路径（与CMD文件格式一致）
                    try:
                        rel_path = os.path.relpath(abs_script_path, work_dir)
                        rel_path_normalized = rel_path.replace('/', '\\')
                    except ValueError:
                        # 如果无法计算相对路径，使用绝对路径
                        rel_path_normalized = abs_script_path.replace('/', '\\')
                    # 使用与CMD文件相同的格式：start "窗口标题" cmd /k "python 相对路径"
                    # 这样工作目录会自动设置为当前目录（项目根目录）
                    start_command = f'start "{window_title}" cmd /k "cd /d {work_dir} && python {rel_path_normalized}"'
                    process = subprocess.Popen(
                        start_command,
                        shell=True,  # 使用shell=True来执行start命令
                        cwd=work_dir,  # 设置工作目录
                        creationflags=subprocess.CREATE_NO_WINDOW  # 隐藏启动命令本身的窗口
                    )
                    # 注意：使用start命令时，返回的process是start命令的进程，不是客户端进程
                    # 实际客户端会在新窗口中运行
                    logger.info(f"客户端 {i + 1} 已在新窗口中启动")
                    logger.info(f"  原始路径: {script_path}")
                    logger.info(f"  绝对路径: {abs_script_path}")
                    logger.info(f"  相对路径: {rel_path_normalized}")
                    logger.info(f"  工作目录: {work_dir}")
                    logger.info(f"  窗口标题: {window_title}")
                    logger.info(f"  启动命令: {start_command}")
                    logger.info(f"  提示: 如果看不到窗口，请检查任务栏或使用 Alt+Tab 切换")
                    # 创建一个虚拟的进程对象用于跟踪
                    class VirtualProcess:
                        def __init__(self, pid, window_title):
                            self.pid = pid
                            self.returncode = None
                            self.window_title = window_title
                        def poll(self):
                            return self.returncode
                        def terminate(self):
                            # 尝试终止新窗口中的进程
                            try:
                                subprocess.run(['taskkill', '/F', '/FI', f'WINDOWTITLE eq {self.window_title}*'], 
                                             capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                            except:
                                pass
                        def kill(self):
                            self.terminate()
                    process = VirtualProcess(process.pid, window_title)
                else:
                    # Linux/Mac: 使用默认方式
                    process = subprocess.Popen(command)
                
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
