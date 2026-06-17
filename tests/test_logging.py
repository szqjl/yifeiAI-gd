"""
日志系统属性测试

测试日志记录的完整性、格式正确性和双输出功能。
"""

import logging
import os
import tempfile
import shutil
from hypothesis import given, strategies as st, settings
from batch_executor.logging_config import setup_logging, get_logger, log_error_with_stack


def is_printable_message(text: str) -> bool:
    """检查文本是否包含可打印内容（排除控制字符）"""
    if not text.strip():
        return False
    # 排除换行符、回车符和其他控制字符
    for char in text:
        if char in '\r\n\t\f\v\x0b\x0c':
            return False
    return True


class TestLoggingProperties:
    """日志系统属性测试"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.test_log_dir = tempfile.mkdtemp()
        # 清除之前的handlers
        logger = logging.getLogger("batch_executor")
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)
    
    def teardown_method(self):
        """每个测试后的清理"""
        # 清除handlers
        logger = logging.getLogger("batch_executor")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        
        # 删除测试日志目录
        if os.path.exists(self.test_log_dir):
            shutil.rmtree(self.test_log_dir)
    
    @given(message=st.text(min_size=1, max_size=200).filter(is_printable_message))
    @settings(max_examples=100)
    def test_property_17_log_completeness(self, message):
        """
        **Feature: batch-game-execution, Property 17: 日志记录完整性**
        **Validates: Requirements 7.1**
        
        For any 系统操作，该操作应该被记录到日志文件中
        """
        # 设置日志系统
        logger = setup_logging(log_dir=self.test_log_dir, log_level=logging.INFO)
        
        # 记录消息
        logger.info(message)
        
        # 刷新所有handlers
        for handler in logger.handlers:
            handler.flush()
        
        # 查找日志文件
        log_files = [f for f in os.listdir(self.test_log_dir) if f.endswith('.log')]
        assert len(log_files) > 0, "应该创建日志文件"
        
        # 读取日志文件内容
        log_file_path = os.path.join(self.test_log_dir, log_files[0])
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # 验证消息被记录
        assert message in log_content, f"日志文件应该包含消息: {message}"
    
    @given(
        level=st.sampled_from(['INFO', 'WARNING', 'ERROR', 'DEBUG']),
        message=st.text(min_size=1, max_size=100).filter(is_printable_message)
    )
    @settings(max_examples=100)
    def test_property_18_log_format_correctness(self, level, message):
        """
        **Feature: batch-game-execution, Property 18: 日志格式正确性**
        **Validates: Requirements 7.2**
        
        For any 日志条目，应该包含时间戳、操作类型和详细信息
        """
        # 设置日志系统
        logger = setup_logging(log_dir=self.test_log_dir, log_level=logging.DEBUG)
        
        # 根据级别记录消息
        log_method = getattr(logger, level.lower())
        log_method(message)
        
        # 刷新所有handlers
        for handler in logger.handlers:
            handler.flush()
        
        # 读取日志文件
        log_files = [f for f in os.listdir(self.test_log_dir) if f.endswith('.log')]
        log_file_path = os.path.join(self.test_log_dir, log_files[0])
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
        
        # 查找包含消息的行
        matching_lines = [line for line in log_lines if message in line]
        assert len(matching_lines) > 0, "应该找到包含消息的日志行"
        
        log_line = matching_lines[-1]  # 取最后一条匹配的行
        
        # 验证格式：时间戳 - 级别 - 消息
        # 格式示例: 2024-01-01 12:00:00 - INFO - message
        parts = log_line.split(' - ', 2)
        assert len(parts) >= 3, f"日志格式应该包含时间戳、级别和消息，实际: {log_line}"
        
        # 验证时间戳格式 (YYYY-MM-DD HH:MM:SS)
        timestamp = parts[0].strip()
        assert len(timestamp) == 19, f"时间戳格式应该是 YYYY-MM-DD HH:MM:SS，实际: {timestamp}"
        assert timestamp[4] == '-' and timestamp[7] == '-', "时间戳应该包含日期分隔符"
        assert timestamp[10] == ' ', "时间戳应该包含日期和时间分隔符"
        assert timestamp[13] == ':' and timestamp[16] == ':', "时间戳应该包含时间分隔符"
        
        # 验证级别
        log_level = parts[1].strip()
        assert log_level == level, f"日志级别应该是 {level}，实际: {log_level}"
        
        # 验证消息（日志系统可能会规范化空白字符）
        log_message = parts[2].strip()
        # 消息内容应该匹配（忽略首尾空白）
        assert message.strip() in log_message or message in log_message, f"日志消息应该包含 {message}"

    @given(message=st.text(min_size=1, max_size=100).filter(is_printable_message))
    @settings(max_examples=100)
    def test_property_20_log_dual_output(self, message):
        """
        **Feature: batch-game-execution, Property 20: 日志双输出**
        **Validates: Requirements 7.5**
        
        For any 日志条目，应该同时出现在控制台和日志文件中
        """
        import io
        import sys
        
        # 捕获控制台输出
        captured_output = io.StringIO()
        
        # 设置日志系统
        logger = setup_logging(log_dir=self.test_log_dir, log_level=logging.INFO)
        
        # 替换控制台handler的stream以捕获输出
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.stream = captured_output
        
        # 记录消息
        logger.info(message)
        
        # 刷新所有handlers
        for handler in logger.handlers:
            handler.flush()
        
        # 验证控制台输出
        console_output = captured_output.getvalue()
        assert message in console_output, f"控制台应该包含消息: {message}"
        
        # 验证文件输出
        log_files = [f for f in os.listdir(self.test_log_dir) if f.endswith('.log')]
        assert len(log_files) > 0, "应该创建日志文件"
        
        log_file_path = os.path.join(self.test_log_dir, log_files[0])
        with open(log_file_path, 'r', encoding='utf-8') as f:
            file_output = f.read()
        
        assert message in file_output, f"日志文件应该包含消息: {message}"
    
    @given(error_message=st.text(min_size=1, max_size=100).filter(is_printable_message))
    @settings(max_examples=100, deadline=500)
    def test_property_19_error_log_stack_info(self, error_message):
        """
        **Feature: batch-game-execution, Property 19: 错误日志堆栈信息**
        **Validates: Requirements 7.3**
        
        For any 错误，日志应该包含完整的堆栈跟踪信息
        """
        # 设置日志系统
        logger = setup_logging(log_dir=self.test_log_dir, log_level=logging.ERROR)
        
        # 创建一个异常并记录
        try:
            raise ValueError(error_message)
        except ValueError as e:
            log_error_with_stack(logger, f"测试错误: {error_message}", e)
        
        # 刷新所有handlers
        for handler in logger.handlers:
            handler.flush()
        
        # 读取日志文件
        log_files = [f for f in os.listdir(self.test_log_dir) if f.endswith('.log')]
        log_file_path = os.path.join(self.test_log_dir, log_files[0])
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # 验证错误消息存在
        assert error_message in log_content, f"日志应该包含错误消息: {error_message}"
        
        # 验证堆栈信息存在
        assert "Traceback" in log_content, "日志应该包含堆栈跟踪信息"
        assert "ValueError" in log_content, "日志应该包含异常类型"
        assert "raise ValueError" in log_content, "日志应该包含引发异常的代码行"
