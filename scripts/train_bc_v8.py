"""
V8 BC Training Entry Point — 从 game_records_v8 加载 V8 对战数据，训练 BC 模型。

用法:
    python scripts/train_bc_v8.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

from src.v.nn.training.bc_dataset import load_samples, train_val_split
from src.v.nn.training.bc_trainer import train


def main():
    logger = logging.getLogger("train_bc_v8")

    logger.info("=" * 60)
    logger.info("V8 BC Training Start (game_records_v8)")
    logger.info("=" * 60)

    samples = load_samples(
        record_dir="game_records_v8",
        require_victory_filter=False,
        use_grouping_engine=True,
    )
    logger.info("Loaded %d samples", len(samples))

    if len(samples) < 100:
        logger.error("Too few samples (%d), need at least 100", len(samples))
        logger.info("提示：当前 game_records_v8 只有 9 局 60 副，每副 ~10-20 决策点")
        logger.info("     建议累计更多批跑数据后再训练（至少 27 局 / 180 副）")
        sys.exit(1)

    train_samples, val_samples = train_val_split(samples, val_ratio=0.2)
    logger.info("Train: %d, Val: %d", len(train_samples), len(val_samples))

    record = train(
        train_samples=train_samples,
        val_samples=val_samples,
        lr=5e-4,
        weight_decay=1e-4,
        batch_size=64,
        max_epochs=50,
        patience=10,
        output_dir="models/v-nn",
        model_name="bc_model_v8",
    )

    logger.info("Training complete!")
    logger.info("  Best epoch: %d", record["best_epoch"])
    logger.info("  Best val acc: %.2f%%", record["best_val_acc"] * 100)
    logger.info("  Model saved: %s", record["model_path"])


if __name__ == "__main__":
    main()
