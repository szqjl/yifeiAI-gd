# -*- coding: utf-8 -*-
"""
GUA-038 BC 热启动 CLI — 从 game_records 加载 M3 录牌 → BC 训练 → 保存模型。

用法:
  # 默认参数训练
  python scripts/v7/run_bc_training.py

  # 自定义参数
  python scripts/v7/run_bc_training.py ^
      --data-dir game_records ^
      --output-dir models/v-nn ^
      --model-name bc_model_v1 ^
      --batch-size 128 --lr 1e-3 --max-epochs 100

  # 从已有模型热启动
  python scripts/v7/run_bc_training.py --model-path models/v-nn/bc_model.pth

  # 快速测试（仅读 5 个记录）
  python scripts/v7/run_bc_training.py --max-records 5 --max-epochs 3
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# 将项目根目录加入 path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_bc_training")


def parse_args(argv: list = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GUA-038 BC 热启动 — M3 数据蒸馏训练",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 数据
    parser.add_argument("--data-dir", default="game_records",
                        help="game_records 录牌目录 (default: game_records)")
    parser.add_argument("--max-records", type=int, default=None,
                        help="最多读取的记录数 (default: 全部)")
    parser.add_argument("--no-victory-filter", action="store_true",
                        help="关闭 victoryNum[0]>=2 过滤 (default: 开启)")
    parser.add_argument("--player-filter", default=None,
                        help="玩家名过滤 (default: 自动识别 yf 玩家)")

    # 模型
    parser.add_argument("--model-path", default=None,
                        help="已有模型检查点路径 (default: 新建模型)")
    parser.add_argument("--output-dir", default="models/v-nn",
                        help="模型输出目录 (default: models/v-nn)")
    parser.add_argument("--model-name", default="bc_model",
                        help="模型文件名 (default: bc_model)")

    # 训练
    parser.add_argument("--batch-size", type=int, default=64,
                        help="批大小 (default: 64)")
    parser.add_argument("--lr", type=float, default=1e-3,
                        help="学习率 (default: 1e-3)")
    parser.add_argument("--weight-decay", type=float, default=1e-4,
                        help="权重衰减 (default: 1e-4)")
    parser.add_argument("--max-epochs", type=int, default=50,
                        help="最大训练轮数 (default: 50)")
    parser.add_argument("--patience", type=int, default=5,
                        help="早停 patience (default: 5)")
    parser.add_argument("--seed", type=int, default=42,
                        help="随机种子 (default: 42)")

    # GUA-061: 组牌引擎
    parser.add_argument("--use-grouping-engine", action="store_true",
                        help="使用 GUA-061 grouping_engine 24 维（默认 GUA-054 grouping_scanner 9 维）")

    # 其他
    parser.add_argument("--dry-run", action="store_true",
                        help="仅加载数据并打印统计，不训练")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="详细日志")

    return parser.parse_args(argv)


def print_summary(train_samples, val_samples, record: Dict[str, Any]):
    """打印训练摘要。"""
    logger.info("=" * 60)
    logger.info("BC 训练摘要")
    logger.info("=" * 60)
    logger.info("  总样本:     %d", len(train_samples) + len(val_samples))
    logger.info("  训练样本:   %d", len(train_samples))
    logger.info("  验证样本:   %d", len(val_samples))
    logger.info("  最佳轮次:   %d", record.get("best_epoch", "N/A"))
    logger.info("  最佳验证准确率: %.2f%%", record.get("best_val_acc", 0) * 100)
    logger.info("  最佳验证 loss:  %.4f", record.get("best_val_loss", float("inf")))
    logger.info("  训练 %d 轮 (早停: %s)",
                record.get("total_epochs", 0),
                "是" if record.get("stopped_early") else "否")
    logger.info("  模型保存:   %s", record.get("model_path", "N/A"))
    logger.info("=" * 60)


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── 1. 加载 ──
    logger.info("正在从 %s 加载 BC 训练样本...", args.data_dir)
    logger.info("  过滤: victory=%s, player=%s, max_records=%s",
                "是" if not args.no_victory_filter else "否",
                args.player_filter or "yf*",
                args.max_records or "全部")

    from src.v.nn.training.bc_dataset import load_samples, train_val_split

    samples = load_samples(
        record_dir=args.data_dir,
        max_records=args.max_records,
        require_victory_filter=not args.no_victory_filter,
        player_filter=args.player_filter,
        use_grouping_engine=args.use_grouping_engine,
    )

    if not samples:
        logger.error("没有加载到任何样本! 检查 data-dir: %s", args.data_dir)
        sys.exit(1)

    logger.info("共加载 %d 条样本", len(samples))

    # ── 2. 切分 ──
    train_samples, val_samples = train_val_split(
        samples, val_ratio=0.2, shuffle=True, seed=args.seed,
    )

    logger.info("训练集: %d | 验证集: %d", len(train_samples), len(val_samples))

    # ── 3. Dry-run ──
    if args.dry_run:
        logger.info("Dry-run 模式，跳过训练")
        logger.info("样本来源文件分布:")
        from collections import Counter
        sources = Counter(s.source_file for s in samples)
        for src, cnt in sources.most_common(10):
            logger.info("  %s: %d 条", Path(src).name, cnt)
        return

    # ── 4. 训练 ──
    logger.info("开始 BC 训练...")
    logger.info("  参数: lr=%.0e wd=%.0e bs=%d epochs=%d patience=%d",
                args.lr, args.weight_decay, args.batch_size,
                args.max_epochs, args.patience)

    from src.v.nn.training.bc_trainer import load_model, train

    model = None
    if args.model_path:
        model = load_model(model_path=args.model_path)

    record = train(
        train_samples=train_samples,
        val_samples=val_samples,
        model=model,
        lr=args.lr,
        weight_decay=args.weight_decay,
        batch_size=args.batch_size,
        max_epochs=args.max_epochs,
        patience=args.patience,
        output_dir=args.output_dir,
        model_name=args.model_name,
        seed=args.seed,
    )

    print_summary(train_samples, val_samples, record)

    # ── 5. 验证验收标准 ──
    val_acc = record.get("best_val_acc", 0)
    if val_acc > 0.60:
        logger.info("✓ 验收通过: 验证准确率 %.2f%% > 60%%", val_acc * 100)
    else:
        logger.warning("! 验收未达 60%%: 验证准确率 %.2f%%, 需更多数据或调参", val_acc * 100)


if __name__ == "__main__":
    main()