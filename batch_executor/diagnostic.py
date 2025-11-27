"""
诊断模块

用于诊断服务器为何只执行3场游戏的根本原因。
"""

import os
import re
import subprocess
import threading
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DiagnosticReport:
    """诊断报告"""
    config_files_found: List[str]
    server_output: str
    expected_count: int
    actual_count: Optional[int]
    mismatch_detected: bool
    possible_causes: List[str]
    recommendations: List[str]


class DiagnosticModule:
    """诊断服务器参数问题的模块"""
    
    # 常见配置文件名称
    CONFIG_FILE_PATTERNS = [
        'config.ini',
        'config.json',
        'config.yaml',
        'config.yml',
        'settings.txt',
        'settings.ini',
        'settings.json',
        'configuration.ini',
        'configuration.json',
        '.config',
        'app.config',
    ]
    
    def check_config_files(self, server_dir: str) -> List[str]:
        """
        检查服务器目录中的配置文件
        
        Args:
            server_dir: 服务器目录路径
            
        Returns:
            找到的配置文件列表（相对于server_dir的路径）
        """
        if not os.path.exists(server_dir):
            return []
        
        if not os.path.isdir(server_dir):
            return []
        
        found_files = []
        
        try:
            # 遍历目录中的所有文件
            for item in os.listdir(server_dir):
                item_path = os.path.join(server_dir, item)
                
                # 只检查文件，不递归子目录
                if os.path.isfile(item_path):
                    # 检查文件名是否匹配配置文件模式
                    if item.lower() in [p.lower() for p in self.CONFIG_FILE_PATTERNS]:
                        found_files.append(item)
        except (PermissionError, OSError):
            # 如果无法访问目录，返回空列表
            return []
        
        return sorted(found_files)
    
    def capture_server_output(self, process, timeout: int = 10) -> str:
        """
        捕获服务器启动输出
        
        使用线程异步读取进程的stdout和stderr，避免阻塞。
        
        Args:
            process: subprocess.Popen 进程对象
            timeout: 捕获超时时间（秒）
            
        Returns:
            捕获到的输出内容（stdout和stderr合并）
        """
        if process is None:
            return ""
        
        output_lines = []
        
        def read_stream(stream, output_list):
            """读取流并添加到输出列表"""
            if stream is None:
                return
            try:
                for line in stream:
                    if isinstance(line, bytes):
                        line = line.decode('utf-8', errors='ignore')
                    output_list.append(line.rstrip())
            except Exception:
                pass
        
        # 创建线程读取stdout和stderr
        threads = []
        
        if process.stdout:
            stdout_thread = threading.Thread(
                target=read_stream,
                args=(process.stdout, output_lines)
            )
            stdout_thread.daemon = True
            stdout_thread.start()
            threads.append(stdout_thread)
        
        if process.stderr:
            stderr_thread = threading.Thread(
                target=read_stream,
                args=(process.stderr, output_lines)
            )
            stderr_thread.daemon = True
            stderr_thread.start()
            threads.append(stderr_thread)
        
        # 等待线程完成或超时
        for thread in threads:
            thread.join(timeout=timeout)
        
        return '\n'.join(output_lines)
    
    def extract_game_count(self, output: str) -> Optional[int]:
        """
        从服务器输出中提取游戏次数
        
        支持多种输出格式：
        - "Game count: 100"
        - "游戏次数: 100"
        - "游戏场数: 100"
        - "Total games: 100"
        - "Games: 100"
        - "Count: 100"
        
        Args:
            output: 服务器输出内容
            
        Returns:
            提取到的游戏次数，如果未找到则返回None
        """
        if not output:
            return None
        
        # 定义多种可能的模式
        patterns = [
            r'[Gg]ame\s+[Cc]ount\s*[:：]\s*(\d+)',
            r'游戏次数\s*[:：]\s*(\d+)',
            r'游戏场数\s*[:：]\s*(\d+)',
            r'[Tt]otal\s+[Gg]ames\s*[:：]\s*(\d+)',
            r'[Gg]ames\s*[:：]\s*(\d+)',
            r'[Cc]ount\s*[:：]\s*(\d+)',
            r'场数\s*[:：]\s*(\d+)',
        ]
        
        # 尝试每个模式
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def diagnose(self, expected: int, actual: Optional[int], 
                 config_files: List[str], server_output: str) -> DiagnosticReport:
        """
        诊断参数不匹配的原因
        
        Args:
            expected: 期望的游戏次数（命令行参数）
            actual: 实际的游戏次数（从服务器输出提取）
            config_files: 找到的配置文件列表
            server_output: 服务器输出内容
            
        Returns:
            诊断报告
        """
        mismatch_detected = False
        possible_causes = []
        recommendations = []
        
        # 检查是否存在不匹配
        if actual is None:
            mismatch_detected = True
            possible_causes.append("无法从服务器输出中提取游戏次数")
            recommendations.append("检查服务器是否正确输出游戏次数信息")
            recommendations.append("查看服务器文档确认输出格式")
        elif actual != expected:
            mismatch_detected = True
            possible_causes.append(f"命令行参数指定 {expected} 场，但服务器实际设置为 {actual} 场")
            
            # 分析可能的原因
            if config_files:
                possible_causes.append(f"发现配置文件: {', '.join(config_files)}，可能覆盖了命令行参数")
                recommendations.append("检查配置文件中的游戏次数设置")
                recommendations.append("尝试修改或删除配置文件")
            else:
                possible_causes.append("未发现配置文件，可能是服务器内部硬编码限制")
                recommendations.append("检查服务器源代码或文档")
                recommendations.append("联系服务器开发者确认参数处理逻辑")
            
            if actual == 3:
                possible_causes.append("服务器可能有默认的3场限制")
                recommendations.append("这可能是服务器的默认行为或测试模式")
            
            recommendations.append("使用批量执行系统自动重启来完成目标场数")
        else:
            # 没有不匹配
            recommendations.append("参数设置正确，可以正常执行")
        
        return DiagnosticReport(
            config_files_found=config_files,
            server_output=server_output,
            expected_count=expected,
            actual_count=actual,
            mismatch_detected=mismatch_detected,
            possible_causes=possible_causes,
            recommendations=recommendations
        )
