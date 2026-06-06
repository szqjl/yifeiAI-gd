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
        visible_server: bool = False,  # Add this parameter
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
        # 在启动服务器之前，先清理所有服务器进程（避免端口冲突）
        logger.info("启动服务器前清理所有服务器进程...")
        process_names = ['guandan_offline_v1006.exe']
        self.process_monitor.kill_all(process_names)
        # 额外等待1秒，确保进程完全终止
        time.sleep(1)
        logger.info("服务器进程清理完成")
        
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
                # 如果game_count是single_run_limit（3），不传递参数让服务器无限运行
                # 这样可以通过外部控制来停止服务器，而不是让服务器自己决定何时停止
                if game_count == 3:  # single_run_limit的默认值
                    command = [server_path]  # 不传递参数，让服务器无限运行
                    logger.info("使用无限运行模式启动服务器（不传递游戏次数参数）")
                else:
                    command = [server_path, str(game_count)]
                
                # 获取服务器所在目录作为工作目录
                server_dir = os.path.dirname(server_path) or "."
                logger.info(f"工作目录: {server_dir}")
                
                # 启动服务器进程
                # 捕获输出以便读取战绩，但不阻塞
                creationflags = 0
                if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    creationflags = subprocess.CREATE_NO_WINDOW

                if visible_server and sys.platform == 'win32':
                    if hasattr(subprocess, 'CREATE_NEW_CONSOLE'):
                        creationflags = subprocess.CREATE_NEW_CONSOLE
                    else:
                        # Fallback for older Python versions
                        creationflags = 0  # Let it create default window

                process = subprocess.Popen(
                    command,
                    cwd=server_dir,  # 设置工作目录
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,  # 设置创建标志
                    text=True,
                    bufsize=1  # 行缓冲
                )
                
                logger.info(f"服务器进程已启动，PID: {process.pid}")
                
                # Enhanced waiting loop with real-time stdout reading
                check_interval = 2
                elapsed = 0
                server_output_lines = []

                logger.info(f"服务器窗口已启动，PID: {process.pid}")
                logger.info("等待服务器输出 'ready for connect' 或类似就绪消息...")

                while elapsed < wait_time:
                    time.sleep(min(check_interval, wait_time - elapsed))
                    elapsed += check_interval
                    
                    # Try to read available stdout lines (may be limited in CREATE_NEW_CONSOLE mode)
                    try:
                        if process.stdout:
                            while True:
                                line = process.stdout.readline()
                                if not line:
                                    break
                                line = line.strip()
                                if line:
                                    server_output_lines.append(line)
                                    logger.info(f"[服务器] {line}")
                                    # Check for readiness message
                                    if any(keyword in line.lower() for keyword in ["ready for connect", "server started", "listening", "waiting for players", "ready"]):
                                        logger.info("✓ 检测到服务器就绪消息!")
                                        # We can break early if ready message found
                                        elapsed = wait_time  # Force exit loop
                                        break
                    except Exception as read_error:
                        # In CREATE_NEW_CONSOLE mode, stdout might not be available
                        logger.debug(f"读取服务器输出时出错 (正常在可见窗口模式): {read_error}")
                    
                    # Check process status
                    return_code = process.poll()
                    if return_code is not None:
                        logger.warning(f"服务器进程在 {elapsed} 秒后退出，返回码: {return_code}")
                        # Read any remaining output
                        try:
                            if process.stdout:
                                remaining = process.stdout.read()
                                if remaining:
                                    remaining_lines = [line.strip() for line in remaining.splitlines() if line.strip()]
                                    server_output_lines.extend(remaining_lines)
                                    for line in remaining_lines[-5:]:
                                        logger.info(f"[服务器最终输出] {line}")
                        except:
                            pass
                        break

                # If using visible window, check port instead of stdout
                if visible_server and sys.platform == 'win32':
                    logger.info("服务端窗口已可见，检查端口是否监听...")
                    # Try to detect if port 23456 is listening
                    import socket
                    port_ready = False
                    for _ in range(5):  # Try 5 times
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(1)
                            result = sock.connect_ex(('127.0.0.1', 23456))
                            sock.close()
                            if result == 0:
                                logger.info("✓ 检测到服务器端口23456已监听!")
                                port_ready = True
                                break
                        except:
                            pass
                        time.sleep(1)
                    
                    if not port_ready:
                        logger.warning("未能检测到端口监听，但继续执行（服务器可能需要更多时间）")
                    logger.info("如果连接失败，请检查服务器窗口输出")

                # Log captured output summary
                if server_output_lines:
                    logger.info(f"捕获到服务器输出 {len(server_output_lines)} 行 (最后5行):")
                    for line in server_output_lines[-5:]:
                        logger.info(f"  {line}")
                else:
                    if visible_server:
                        logger.info("无捕获输出 (正常，可见窗口模式)，请查看弹出的服务端窗口")
                    else:
                        logger.warning("无服务器输出，服务器可能未正常启动")

                # Final check - 确保服务器进程仍在运行
                if process.poll() is None:
                    # 再次验证端口是否监听（额外检查）
                    import socket
                    port_ready = False
                    for check_attempt in range(3):
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(1)
                            result = sock.connect_ex(('127.0.0.1', 23456))
                            sock.close()
                            if result == 0:
                                logger.info(f"✓ 验证成功: 服务器端口23456已监听 (检查 {check_attempt + 1}/3)")
                                port_ready = True
                                break
                        except Exception as e:
                            logger.debug(f"端口检查 {check_attempt + 1} 失败: {e}")
                        if check_attempt < 2:
                            time.sleep(1)
                    
                    if port_ready or visible_server:
                        # 如果端口就绪，或者服务器窗口可见（可能无法检测端口），认为启动成功
                        logger.info("✓ 服务器启动成功，进程正在运行")
                        if not port_ready and visible_server:
                            logger.info("  注意: 服务器窗口可见，无法验证端口，但进程正在运行")
                        self.server_process = process
                        return process
                    else:
                        logger.warning("⚠️ 服务器进程运行中，但端口23456未监听")
                        logger.warning("  可能原因: 服务器需要更多时间启动，或端口配置不同")
                        # 即使端口未监听，如果进程在运行，也返回（可能是服务器启动较慢）
                        self.server_process = process
                        return process
                else:
                    return_code = process.returncode
                    logger.error(f"✗ 服务器进程已终止，返回码: {return_code}")
                    if server_output_lines:
                        logger.error("服务器错误输出 (最后20行):")
                        for line in server_output_lines[-20:]:
                            logger.error(f"  {line}")
                    else:
                        logger.error("提示: 服务器可能启动失败，请检查:")
                        logger.error("  1. 服务器路径是否正确")
                        logger.error("  2. 服务器参数是否正确（游戏场数）")
                        logger.error("  3. 是否有权限执行服务器")
                        logger.error("  4. 端口23456是否被占用")
                        logger.error("  5. 服务器依赖文件是否完整")
                    
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
        wait_between: int = 8  # 8 seconds between clients to ensure connection order (increased for client startup and internal delay)
    ) -> List[subprocess.Popen]:
        """
        重启所有客户端
        
        按顺序启动所有客户端，每个客户端之间等待指定时间。
        处理启动失败，继续启动其他客户端。
        
        Args:
            client_scripts: 客户端脚本路径列表
            wait_between: 每个客户端之间的等待时间（秒），默认8秒
            
        Returns:
            成功启动的客户端进程列表
        """
        # 验证客户端脚本列表，确保没有重复
        seen_scripts = set()
        for script in client_scripts:
            script_name = os.path.basename(script).lower()
            if script_name in seen_scripts:
                logger.error(f"⚠️ 发现重复的客户端脚本: {script}")
                logger.error(f"   客户端脚本列表: {client_scripts}")
            seen_scripts.add(script_name)
        
        if len(seen_scripts) != len(client_scripts):
            logger.warning(f"⚠️ 客户端脚本列表可能有重复，已发现 {len(seen_scripts)} 个唯一脚本，但列表有 {len(client_scripts)} 个")
        
        logger.info("=" * 60)
        logger.info("客户端启动顺序验证")
        logger.info("=" * 60)
        for i, script in enumerate(client_scripts):
            script_name = os.path.basename(script)
            logger.info(f"  {i+1}. {script_name}")
        logger.info("=" * 60)
        
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
                    # Windows: 使用start命令创建带标题的控制台窗口，显示客户端输出
                    work_dir = str(self.project_root.resolve())
                    script_name = os.path.basename(abs_script_path)
                    window_title = f"客户端{i+1}: {script_name}"
                    
                    # 使用start命令创建带标题的新窗口
                    # start "窗口标题" cmd /k "python 脚本路径"
                    # /k 参数表示执行后保持窗口打开
                    try:
                        rel_path = os.path.relpath(abs_script_path, work_dir)
                        rel_path_normalized = rel_path.replace('/', '\\')
                    except ValueError:
                        rel_path_normalized = abs_script_path.replace('/', '\\')
                    
                    start_command = f'start "{window_title}" cmd /k "cd /d {work_dir} && python {rel_path_normalized}"'
                    
                    process = subprocess.Popen(
                        start_command,
                        shell=True,
                        cwd=work_dir,
                        creationflags=subprocess.CREATE_NO_WINDOW  # 隐藏启动命令本身的窗口
                    )
                    
                    logger.info(f"客户端 {i + 1} 已启动 (新控制台窗口，标题: {window_title})")
                    logger.info(f"  原始路径: {script_path}")
                    logger.info(f"  绝对路径: {abs_script_path}")
                    logger.info(f"  工作目录: {work_dir}")
                    logger.info(f"  窗口标题: {window_title}")
                    logger.info(f"  PID: {process.pid}")
                    
                    # 创建一个虚拟进程对象用于跟踪（start命令返回的是start进程，不是客户端进程）
                    class VirtualProcess:
                        def __init__(self, pid, window_title, script_name):
                            self.pid = pid
                            self.returncode = None
                            self.window_title = window_title
                            self.script_name = script_name
                        def poll(self):
                            # 检查python进程是否还存在（通过tasklist查找包含脚本名的python进程）
                            try:
                                result = subprocess.run(
                                    ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV', '/V'],
                                    capture_output=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                    timeout=2
                                )
                                output = result.stdout.decode('gbk', errors='ignore')
                                # 检查是否有python进程包含我们的脚本名
                                if self.script_name.lower() in output.lower():
                                    return None  # 进程还在运行
                                else:
                                    return 0  # 进程已结束
                            except:
                                return None  # 检查失败，假设进程还在
                        def terminate(self):
                            # 通过窗口标题终止进程
                            try:
                                subprocess.run(
                                    ['taskkill', '/F', '/FI', f'WINDOWTITLE eq {self.window_title}*'],
                                    capture_output=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                    timeout=3
                                )
                            except:
                                pass
                        def kill(self):
                            self.terminate()
                    
                    process = VirtualProcess(process.pid, window_title, script_name)
                else:
                    # Linux/Mac: 使用默认方式
                    process = subprocess.Popen(command)
                
                logger.info(f"客户端 {i + 1} 已启动，PID: {process.pid}")
                processes.append(process)
                
                # 等待后再启动下一个客户端 (确保顺序连接)
                # 客户端内部延迟（与脚本内 DELAY / _lalala_launcher 对齐）：
                # yf1_v7=2s, run_lalala_client3=3s, yf2_v7=4s, run_lalala_client4=6s
                if i < len(client_scripts) - 1:
                    current_script = os.path.basename(script_path).lower()
                    if 'yf1_v7' in current_script:
                        wait_time = 4
                        logger.info(f"等待 {wait_time} 秒（yf1_v7 内部延迟 2s + 缓冲）...")
                    elif 'yf1_m1' in current_script:
                        wait_time = 6
                        logger.info(f"等待 {wait_time} 秒（yf1_m1需要5秒内部延迟，确保它开始连接后再启动下一个）...")
                    elif 'run_lalala_client3' in current_script or (
                        'client3' in current_script and 'lalala' in current_script
                    ):
                        wait_time = 5
                        logger.info(f"等待 {wait_time} 秒（run_lalala_client3 内部延迟 3s + 缓冲）...")
                    elif 'client3' in current_script:
                        wait_time = 11
                        logger.info(f"等待 {wait_time} 秒（client3需要10秒内部延迟，确保它开始连接后再启动下一个）...")
                    elif 'yf2_v7' in current_script:
                        wait_time = 6
                        logger.info(f"等待 {wait_time} 秒（yf2_v7 内部延迟 4s + 缓冲）...")
                    elif 'yf2_m1' in current_script:
                        wait_time = 16
                        logger.info(f"等待 {wait_time} 秒（yf2_m1需要15秒内部延迟，确保它开始连接后再启动下一个）...")
                    elif 'run_lalala_client4' in current_script or (
                        'client4' in current_script and 'lalala' in current_script
                    ):
                        wait_time = 8
                        logger.info(f"等待 {wait_time} 秒（run_lalala_client4 内部延迟 6s + 缓冲）...")
                    else:
                        wait_time = wait_between
                        logger.info(f"等待 {wait_time} 秒后启动下一个客户端（确保连接顺序）...")
                    
                    logger.info(f"⏳ 等待中... ({wait_time}秒)")
                    time.sleep(wait_time)
                    logger.info(f"✓ 等待完成，准备启动下一个客户端")
                    
                    # 验证当前客户端进程仍在运行
                    if process.poll() is None:
                        logger.info(f"✓ 客户端 {i + 1} 进程运行正常")
                    else:
                        logger.warning(f"⚠ 客户端 {i + 1} 进程已退出，返回码: {process.returncode}")
                    
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
    
    def wait_for_clients_connected(
        self,
        expected_count: int = 4,
        timeout: int = 30,
        check_interval: int = 2,
        expected_client_ids: Optional[List[str]] = None,
    ) -> bool:
        """
        等待所有客户端 WebSocket 就绪（读取 batch_executor/clients_ready.json）。

        Args:
            expected_count: 期望连接的客户端数量
            timeout: 超时时间（秒）
            check_interval: 轮询间隔（秒）
            expected_client_ids: 各席 user_info；缺省时仅按数量判断

        Returns:
            四席全部登记就绪返回 True
        """
        from batch_executor.client_ready import count_ready, get_ready_clients, wait_for_all_clients

        targets = list(expected_client_ids) if expected_client_ids else []

        logger.info(f"等待 {expected_count} 个客户端 WebSocket 就绪...")
        logger.info(f"超时时间: {timeout} 秒，就绪表: batch_executor/clients_ready.json")
        if targets:
            logger.info(f"期望席位: {', '.join(targets)}")

        if targets:
            ok = wait_for_all_clients(
                targets,
                timeout=float(timeout),
                poll_interval=float(check_interval),
            )
            if ok:
                ready = get_ready_clients()
                logger.info("✓ 四席已全部连上并就绪（末席连入后平台将开局）")
                for cid in targets:
                    ts = ready.get(cid, {}).get("timestamp", "?")
                    logger.info(f"  - {cid}: {ts}")
                return True
            ready = get_ready_clients()
            missing = [cid for cid in targets if cid not in ready]
            logger.warning(f"⚠️ 等待客户端就绪超时 ({timeout}s)")
            logger.warning(f"   已就绪: {list(ready.keys())}")
            logger.warning(f"   未就绪: {missing}")
            logger.warning("   建议: 查看各客户端控制台是否有「前序席位未就绪」或连接错误")
            return False

        start = time.time()
        while time.time() - start < timeout:
            n = count_ready()
            if n >= expected_count:
                logger.info(f"✓ 就绪席位数 {n}/{expected_count}")
                return True
            time.sleep(check_interval)
        logger.warning(f"⚠️ 就绪席位不足: {count_ready()}/{expected_count}")
        return False
    def cleanup(self) -> None:
        """
        清理所有进程
        
        终止所有服务器和客户端进程，释放资源。
        确保彻底清理，包括通过窗口标题查找的客户端进程。
        """
        logger.info("=" * 60)
        logger.info("开始清理所有进程...")
        logger.info("=" * 60)
        
        # 第一步：终止所有已知的客户端进程
        logger.info("步骤1: 终止已知的客户端进程...")
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
        
        # 第二步：通过窗口标题清理所有客户端窗口（Windows）
        if sys.platform == 'win32':
            logger.info("步骤2: 通过窗口标题清理所有客户端窗口...")
            client_window_titles = [
                "客户端1:", "客户端2:", "客户端3:", "客户端4:",
                "client1:", "client2:", "client3:", "client4:"
            ]
            for title in client_window_titles:
                try:
                    # 使用taskkill通过窗口标题终止进程
                    result = subprocess.run(
                        ['taskkill', '/F', '/FI', f'WINDOWTITLE eq {title}*'],
                        capture_output=True,
                        timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if result.returncode == 0:
                        logger.info(f"已清理窗口标题包含 '{title}' 的进程")
                except Exception as e:
                    logger.debug(f"清理窗口标题 '{title}' 时出错: {e}")
        
        # 第三步：终止服务器进程
        logger.info("步骤3: 终止服务器进程...")
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
        
        # 第四步：使用进程监控器确保服务器进程已终止
        logger.info("步骤4: 确保所有服务器进程已终止...")
        process_names = ['guandan_offline_v1006.exe']
        self.process_monitor.kill_all(process_names)
        
        # 第五步：等待一小段时间，确保所有进程完全终止
        logger.info("步骤5: 等待进程完全终止...")
        time.sleep(2)
        
        # 第六步：验证清理结果
        logger.info("步骤6: 验证清理结果...")
        remaining_servers = 0
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'guandan_offline_v1006.exe':
                        remaining_servers += 1
                        logger.warning(f"发现残留的服务器进程: PID {proc.pid}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.debug(f"验证清理结果时出错: {e}")
        
        if remaining_servers == 0:
            logger.info("✓ 所有服务器进程已清理")
        else:
            logger.warning(f"⚠️ 仍有 {remaining_servers} 个服务器进程未清理，将再次尝试...")
            self.process_monitor.kill_all(process_names)
            time.sleep(1)
        
        # 清空进程列表
        self.client_processes = []
        self.server_process = None
        
        logger.info("=" * 60)
        logger.info("清理完成")
        logger.info("=" * 60)