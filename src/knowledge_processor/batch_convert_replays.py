# -*- coding: utf-8 -*-
"""
批量转换.rep文件为训练数据
支持批量转换、进度显示、错误处理
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.knowledge_processor.platform_replay_converter import (
    convert_rep_to_training_format,
    convert_to_replay_parser_format,
    get_winner_from_rep
)
import json
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_convert.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BatchReplayConverter:
    """批量转换.rep文件"""
    
    def __init__(self, rep_dir: str, output_dir: str = "game_records", prefer_winner: bool = True):
        """
        初始化批量转换器
        
        Args:
            rep_dir: .rep文件所在目录
            output_dir: 输出目录
            prefer_winner: 是否优先选择获胜玩家
        """
        self.rep_dir = Path(rep_dir)
        self.output_dir = Path(output_dir)
        self.prefer_winner = prefer_winner
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 统计信息
        self.stats = {
            'total_files': 0,
            'converted': 0,
            'failed': 0,
            'skipped': 0,
            'total_samples': 0,
            'start_time': None,
            'end_time': None
        }
        
    def find_rep_files(self) -> list:
        """查找所有.rep文件"""
        rep_files = []
        for root, dirs, files in os.walk(self.rep_dir):
            for file in files:
                if file.endswith('.rep'):
                    rep_files.append(Path(root) / file)
        return sorted(rep_files)
    
    def is_already_converted(self, rep_file: Path) -> bool:
        """检查.rep文件是否已经转换"""
        # 检查是否已存在对应的JSON文件
        rep_name = rep_file.stem
        for json_file in self.output_dir.glob(f"*{rep_name}*.json"):
            if 'replay_player' in json_file.name:
                return True
        return False
    
    def convert_single_file(self, rep_file: Path, target_player_id: Optional[int] = None) -> dict:
        """
        转换单个.rep文件
        
        Returns:
            转换结果字典
        """
        try:
            # 如果prefer_winner=True且未指定玩家，自动识别获胜玩家
            if self.prefer_winner and target_player_id is None:
                winner_seat = get_winner_from_rep(str(rep_file))
                if winner_seat is not None:
                    target_player_id = winner_seat
            
            # 转换文件
            training_data = convert_rep_to_training_format(
                str(rep_file),
                target_player_id,
                self.prefer_winner
            )
            
            if not training_data or len(training_data.get("training_samples", [])) == 0:
                return {"success": False, "reason": "No training samples extracted"}
            
            # 转换为ReplayParser格式
            replays = convert_to_replay_parser_format(training_data)
            
            # 保存每个玩家的数据
            saved_files = []
            for replay in replays:
                player_id = replay['player_id']
                output_filename = f"replay_player{player_id}_{rep_file.stem}.json"
                output_path = self.output_dir / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(replay, f, ensure_ascii=False, indent=2)
                
                saved_files.append(output_path)
            
            sample_count = len(training_data["training_samples"])
            return {
                "success": True,
                "samples": sample_count,
                "files": saved_files,
                "players": len(replays)
            }
            
        except Exception as e:
            logger.error(f"转换失败 {rep_file.name}: {str(e)}")
            return {"success": False, "reason": str(e)}
    
    def convert_batch(self, max_files: Optional[int] = None, skip_existing: bool = True):
        """
        批量转换.rep文件
        
        Args:
            max_files: 最大转换文件数（None表示全部）
            skip_existing: 是否跳过已转换的文件
        """
        # 查找所有.rep文件
        all_rep_files = self.find_rep_files()
        self.stats['total_files'] = len(all_rep_files)
        
        # 如果设置了max_files，需要智能处理：
        # 跳过已转换的文件，继续处理未转换的文件，直到达到max_files个成功转换
        if max_files:
            logger.info(f"限制转换数量: {max_files} 个文件（跳过已转换的文件不计入）")
        else:
            logger.info(f"转换所有文件（跳过已转换的文件）")
        
        logger.info(f"找到 {len(all_rep_files)} 个.rep文件")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info(f"优先选择获胜玩家: {self.prefer_winner}")
        logger.info("="*60)
        
        self.stats['start_time'] = time.time()
        
        # 转换每个文件
        processed_count = 0
        for i, rep_file in enumerate(all_rep_files, 1):
            # 检查是否已转换
            if skip_existing and self.is_already_converted(rep_file):
                logger.info(f"[{i}/{len(all_rep_files)}] 跳过已转换: {rep_file.name}")
                self.stats['skipped'] += 1
                continue
            
            # 如果设置了max_files，检查是否已达到目标
            if max_files and self.stats['converted'] >= max_files:
                logger.info(f"已达到转换目标（{max_files}个），停止转换")
                break
            
            processed_count += 1
            
            logger.info(f"[{i}/{len(all_rep_files)}] 转换: {rep_file.name} (已处理: {processed_count}, 已转换: {self.stats['converted']})")
            
            result = self.convert_single_file(rep_file)
            
            if result["success"]:
                self.stats['converted'] += 1
                self.stats['total_samples'] += result["samples"]
                logger.info(f"  ✓ 成功: {result['samples']} 个样本, {result['players']} 个玩家")
            else:
                self.stats['failed'] += 1
                logger.warning(f"  ✗ 失败: {result.get('reason', 'Unknown error')}")
            
            # 每100个文件显示一次进度
            if processed_count % 100 == 0 or (max_files and self.stats['converted'] % 100 == 0):
                self._print_progress()
        
        self.stats['end_time'] = time.time()
        self._print_summary()
    
    def _print_progress(self):
        """打印当前进度"""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['converted'] / elapsed if elapsed > 0 else 0
        remaining_files = self.stats['total_files'] - self.stats['converted'] - self.stats['skipped'] - self.stats['failed']
        remaining = remaining_files / rate if rate > 0 else 0
        
        logger.info("="*60)
        logger.info(f"进度: 成功转换 {self.stats['converted']} 个, "
                   f"跳过 {self.stats['skipped']} 个, "
                   f"失败 {self.stats['failed']} 个")
        logger.info(f"已转换样本: {self.stats['total_samples']} 个")
        if rate > 0:
            logger.info(f"转换速度: {rate:.1f} 文件/秒")
            logger.info(f"预计剩余时间: {remaining/60:.1f} 分钟")
        logger.info("="*60)
    
    def _print_summary(self):
        """打印转换总结"""
        elapsed = self.stats['end_time'] - self.stats['start_time']
        
        logger.info("")
        logger.info("="*60)
        logger.info("批量转换完成！")
        logger.info("="*60)
        logger.info(f"总文件数: {self.stats['total_files']}")
        logger.info(f"成功转换: {self.stats['converted']}")
        logger.info(f"跳过文件: {self.stats['skipped']}")
        logger.info(f"失败文件: {self.stats['failed']}")
        logger.info(f"总训练样本: {self.stats['total_samples']} 个")
        logger.info(f"总耗时: {elapsed/60:.1f} 分钟")
        logger.info(f"平均速度: {self.stats['converted']/elapsed if elapsed > 0 else 0:.1f} 文件/秒")
        logger.info("="*60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量转换.rep文件为训练数据")
    parser.add_argument("--rep_dir", 
                       default=r"C:\Program Files (x86)\gdgame\MobileGD\replay",
                       help=".rep文件目录")
    parser.add_argument("--output_dir", 
                       default="game_records",
                       help="输出目录")
    parser.add_argument("--max_files", 
                       type=int, 
                       default=None,
                       help="最大转换文件数（None表示全部）")
    parser.add_argument("--prefer_winner", 
                       action="store_true", 
                       default=True,
                       help="优先选择获胜玩家")
    parser.add_argument("--no-prefer-winner", 
                       dest="prefer_winner", 
                       action="store_false",
                       help="不优先选择获胜玩家")
    parser.add_argument("--skip-existing", 
                       action="store_true", 
                       default=True,
                       help="跳过已转换的文件")
    parser.add_argument("--no-skip-existing", 
                       dest="skip_existing", 
                       action="store_false",
                       help="不跳过已转换的文件")
    
    args = parser.parse_args()
    
    # 创建转换器
    converter = BatchReplayConverter(
        rep_dir=args.rep_dir,
        output_dir=args.output_dir,
        prefer_winner=args.prefer_winner
    )
    
    # 开始转换
    converter.convert_batch(
        max_files=args.max_files,
        skip_existing=args.skip_existing
    )


if __name__ == "__main__":
    main()

