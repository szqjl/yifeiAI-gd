"""
批量游戏执行系统主入口

提供命令行接口，解析参数并启动批量执行器。
"""

import argparse
import sys
import os
from pathlib import Path

from .logging_config import setup_logging
from .executor import BatchExecutor


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        description='批量游戏执行系统 - 自动管理游戏服务器重启以完成指定场次',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 执行100场游戏（默认）
  python -m batch_executor.main --server-path server.exe
  
  # 执行200场游戏
  python -m batch_executor.main --server-path server.exe --target-games 200
  
  # 仅运行诊断
  python -m batch_executor.main --server-path server.exe --diagnose-only
  
  # 指定客户端脚本
  python -m batch_executor.main --server-path server.exe --clients client1.py client2.py client3.py client4.py
        """
    )
    
    # 必需参数
    parser.add_argument(
        '--server-path',
        type=str,
        required=True,
        help='服务器可执行文件路径（必需）'
    )
    
    # 可选参数
    parser.add_argument(
        '--target-games',
        type=int,
        default=100,
        help='目标游戏场数（默认: 100）'
    )
    
    parser.add_argument(
        '--clients',
        type=str,
        nargs='+',
        default=[],
        help='客户端脚本路径列表（空格分隔）'
    )
    
    parser.add_argument(
        '--diagnose-only',
        action='store_true',
        help='仅运行诊断，不执行游戏'
    )
    
    parser.add_argument(
        '--state-file',
        type=str,
        default='execution_state.json',
        help='执行状态保存文件路径（默认: execution_state.json）'
    )
    
    parser.add_argument(
        '--score-file',
        type=str,
        default='game_scores.json',
        help='战绩保存文件路径（默认: game_scores.json）'
    )
    
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='日志文件目录（默认: logs）'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='日志级别（默认: INFO）'
    )
    
    return parser.parse_args()


def validate_arguments(args):
    """
    验证命令行参数
    
    Args:
        args: 解析后的参数对象
        
    Returns:
        如果验证通过返回True，否则返回False
    """
    # 验证服务器路径
    if not os.path.exists(args.server_path):
        print(f"错误: 服务器文件不存在: {args.server_path}", file=sys.stderr)
        return False
    
    if not os.path.isfile(args.server_path):
        print(f"错误: 服务器路径不是文件: {args.server_path}", file=sys.stderr)
        return False
    
    # 验证目标场数
    if args.target_games <= 0:
        print(f"错误: 目标场数必须是正整数: {args.target_games}", file=sys.stderr)
        return False
    
    # 验证客户端脚本
    for client_path in args.clients:
        if not os.path.exists(client_path):
            print(f"警告: 客户端脚本不存在: {client_path}", file=sys.stderr)
    
    return True


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 验证参数
    if not validate_arguments(args):
        sys.exit(1)
    
    # 设置日志系统
    import logging
    log_level = getattr(logging, args.log_level)
    logger = setup_logging(log_dir=args.log_dir, log_level=log_level)
    
    logger.info("=" * 60)
    logger.info("批量游戏执行系统")
    logger.info("=" * 60)
    logger.info(f"服务器路径: {args.server_path}")
    logger.info(f"目标场数: {args.target_games}")
    logger.info(f"客户端数量: {len(args.clients)}")
    logger.info(f"诊断模式: {'是' if args.diagnose_only else '否'}")
    logger.info("=" * 60)
    
    try:
        # 创建批量执行器
        executor = BatchExecutor(
            target_games=args.target_games,
            server_path=args.server_path,
            client_scripts=args.clients,
            diagnose_only=args.diagnose_only,
            state_file=args.state_file,
            score_file=args.score_file
        )
        
        # 运行
        executor.run()
        
        logger.info("系统正常退出")
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("用户中断执行")
        sys.exit(0)
    except Exception as e:
        logger.error(f"系统异常: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
