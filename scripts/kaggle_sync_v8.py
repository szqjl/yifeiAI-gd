#!/usr/bin/env python3
"""Kaggle 数据同步脚本：将 game_records_v8/ 牌谱重命名后同步到 game_records_v8_kaggle/。

Kaggle 文件名禁止 [] 字符，本脚本将：
  "20260718174914953086 [yf1_v8]-[opponent_1_3]-[1]-[2].json"
  → "20260718174914953086_yf1_v8_opponent_1_3_1_2.json"

用法:
    python scripts/kaggle_sync_v8.py                    # 同步当前 game_records_v8/
    python scripts/kaggle_sync_v8.py --upload           # 同步 + 上传到 Kaggle
    python scripts/kaggle_sync_v8.py --dataset guandanny/guandan-v8-game-records  # 指定数据集
"""
import argparse
import json
import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "game_records_v8"
DST_DIR = PROJECT_ROOT / "game_records_v8_kaggle"

# Kaggle 文件名禁止字符：[] 空格等
# 原始: "20260718... [yf1_v8]-[opponent_1_3]-[1]-[2].json"
# 目标: "20260718..._yf1_v8_opponent_1_3_1_2.json"
_KAGGLE_BRACKET_DASH = re.compile(r"\]-\[")
_KAGGLE_BRACKET = re.compile(r"[\[\]]")
_KAGGLE_SPACE = re.compile(r" +")


def kaggle_filename(orig: str) -> str:
    """将原始文件名转为 Kaggle 兼容文件名。"""
    # 先替换 ]-[ → _，再清除剩余 [ ]，最后空格 → _
    name = _KAGGLE_BRACKET_DASH.sub("_", orig)
    name = _KAGGLE_BRACKET.sub("", name)
    name = _KAGGLE_SPACE.sub("_", name)
    return name


def sync_records(src: Path = SRC_DIR, dst: Path = DST_DIR) -> int:
    """同步 game_records_v8/ → game_records_v8_kaggle/，返回同步文件数。"""
    if not src.is_dir():
        print(f"[ERROR] 源目录不存在: {src}")
        return 0

    dst.mkdir(parents=True, exist_ok=True)

    # 清空目标目录旧文件
    for old in dst.glob("*.json"):
        old.unlink()

    count = 0
    for fp in sorted(src.glob("*.json")):
        new_name = kaggle_filename(fp.name)
        dst_fp = dst / new_name
        shutil.copy2(fp, dst_fp)
        count += 1

    # 生成 dataset-metadata.json
    meta = {
        "title": "Guandan V8 Game Records (Post GUA-151/152/153 Fix)",
        "id": "guandanny/guandan-v8-game-records-post-fix",
        "licenses": [{"name": "CC0-1.0"}],
        "isPrivate": False,
    }
    (dst / "dataset-metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return count


def upload_to_kaggle(dataset: str, dst: Path = DST_DIR):
    """通过 kaggle CLI 上传数据集。需先配置 ~/.kaggle/kaggle.json。"""
    import subprocess
    import sys

    # 检查 kaggle CLI
    try:
        subprocess.run(["kaggle", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[ERROR] kaggle CLI 未安装或不在 PATH。运行: pip install kaggle")
        print("        且需将 kaggle.json 放到 ~/.kaggle/kaggle.json")
        sys.exit(1)

    # 更新 metadata 中的 dataset id
    meta_path = dst / "dataset-metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["id"] = dataset
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[INFO] 上传到 Kaggle 数据集: {dataset}")
    print(f"[INFO] 数据目录: {dst}")
    print(f"[INFO] 文件数: {len(list(dst.glob('*.json')))}")
    result = subprocess.run(
        ["kaggle", "datasets", "upload", "-p", str(dst), "--dir", str(dst)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"[OK] 上传成功: {result.stdout.strip()}")
    else:
        print(f"[ERROR] 上传失败: {result.stderr.strip()}")


def main():
    parser = argparse.ArgumentParser(description="V8 Kaggle 数据同步")
    parser.add_argument("--upload", action="store_true", help="同步后上传到 Kaggle")
    parser.add_argument("--dataset", default="guandanny/guandan-v8-game-records-post-fix",
                        help="Kaggle 数据集 ID (默认: guandanny/guandan-v8-game-records-post-fix)")
    parser.add_argument("--src", default=str(SRC_DIR), help="源目录")
    parser.add_argument("--dst", default=str(DST_DIR), help="目标目录")
    args = parser.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)

    count = sync_records(src, dst)
    print(f"[OK] 同步完成: {count} 个文件 → {dst}")

    if args.upload:
        upload_to_kaggle(args.dataset, dst)


if __name__ == "__main__":
    main()
