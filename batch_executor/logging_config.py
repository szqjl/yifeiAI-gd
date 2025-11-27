"""
日志配置模块

配置系统日志记录，支持控制台和文件双输出。
"""

import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO) -> logging.Logger:
    """
    设置日志系统
    
    Args:
        log_dir: 日志文件目录
        log_level: 日志级别
        
    Returns:
        配置好的logger对象
    """
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建logger
    logger = logging.getLogger("batch_executor")
    logger.setLevel(log_level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 日志格式：时间戳 - 级别 - 消息
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件handler（使用RotatingFileHandler避免日志文件过大）
    log_filename = os.path.join(
        log_dir, 
        f"batch_executor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    file_handler = logging.handlers.RotatingFileHandler(
        log_filename,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"日志系统初始化完成，日志文件: {log_filename}")
    
    return logger


def get_logger() -> logging.Logger:
    """获取logger实例"""
    return logging.getLogger("batch_executor")


def log_error_with_stack(logger: logging.Logger, message: str, exception: Exception = None) -> None:
    """
    记录错误日志并包含完整堆栈信息
    
    Args:
        logger: logger实例
        message: 错误消息
        exception: 异常对象（可选）
    """
    if exception:
        logger.error(message, exc_info=True)
    else:
        logger.error(message, exc_info=True)
