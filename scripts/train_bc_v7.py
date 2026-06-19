"""
GUA-038 BC Training Entry Point (v3 — grouping_engine 24 维)
从 game_records_v7 加载 V7 对战数据，训练 BC 模型并保存到 models/v-nn/bc_model_v3.pth
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
    logger = logging.getLogger("train_bc_v7")

    # Step 1: Load samples from game_records_v7（含 full_state + handCards）
    logger.info("=" * 60)
    logger.info("GUA-061 BC Training Start (grouping_engine 24-dim)")
    logger.info("=" * 60)

    samples = load_samples(
        record_dir="game_records_v7",  # V7 录牌（含 full_state，grouping_engine 需要 handCards）
        require_victory_filter=False,   # V7 数据无 victoryNum，全量使用
        use_grouping_engine=True,       # GUA-061: 使用 grouping_engine 24 维特征
    )
    logger.info("Loaded %d samples", len(samples))
    if len(samples) < 100:
        logger.error("Too few samples (%d), need at least 100", len(samples))
        sys.exit(1)

    # Step 2: Split train/val
    train_samples, val_samples = train_val_split(samples, val_ratio=0.2)

    # Step 3: Train
    # GUA-061 升级：grouping_engine 24 维 → bc_model_v3.pth
    record = train(
        train_samples=train_samples,
        val_samples=val_samples,
        lr=5e-4,
        weight_decay=1e-4,
        batch_size=64,
        max_epochs=50,
        patience=10,
        output_dir="models/v-nn",
        model_name="bc_model_v3",
    )

    logger.info("Training complete!")
    logger.info("  Best epoch: %d", record["best_epoch"])
    logger.info("  Best val acc: %.2f%%", record["best_val_acc"] * 100)
    logger.info("  Model saved: %s", record["model_path"])

    # Verify the model file exists
    model_path = Path(record["model_path"])
    if model_path.exists():
        logger.info("✓ Model file confirmed at: %s", model_path.resolve())
    else:
        logger.error("✗ Model file NOT found at: %s", model_path)


if __name__ == "__main__":
    main()
