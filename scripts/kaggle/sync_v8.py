#!/usr/bin/env python3
"""V8 Kaggle 数据同步脚本。

将 game_records_v8/ 牌谱重命名（去 [] 字符）后同步到 game_records_v8_kaggle/，
并可选打包 zip 供手动上传。

Kaggle 文件名禁止 [] 字符，转换规则：
  "20260718174914953086 [yf1_v8]-[opponent_1_3]-[1]-[2].json"
  → "20260718174914953086_yf1_v8_opponent_1_3_1_2.json"

文件名前缀（时间戳）可用于区分不同批跑：
  20260716... = 修复前数据集
  20260718... = 修复后数据集

用法:
    python scripts/kaggle/sync_v8.py                        # 同步到 game_records_v8_kaggle/
    python scripts/kaggle/sync_v8.py --zip                  # 同步 + 打包 zip（手动上传用）
    python scripts/kaggle/sync_v8.py --upload               # 同步 + CLI 上传（需 kaggle 凭证）
    python scripts/kaggle/sync_v8.py --zip --title "自定义标题"

手动上传步骤（推荐，CLI 有 bug）:
    1. python scripts/kaggle/sync_v8.py --zip
    2. 打开 https://www.kaggle.com/datasets/new
    3. 上传生成的 _kaggle_data.zip
    4. Title 填脚本输出的标题
"""
import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "game_records_v8"
DST_DIR = PROJECT_ROOT / "game_records_v8_kaggle"

# 文件名转换：]-[ → _，清除剩余 []，空格 → _
_BRACKET_DASH = re.compile(r"\]-\[")
_BRACKET = re.compile(r"[\[\]]")
_SPACE = re.compile(r" +")


def kaggle_filename(orig: str) -> str:
    """将原始文件名转为 Kaggle 兼容文件名（去 [] 字符）。"""
    name = _BRACKET_DASH.sub("_", orig)
    name = _BRACKET.sub("", name)
    name = _SPACE.sub("_", name)
    return name


def sync_records(src: Path = SRC_DIR, dst: Path = DST_DIR) -> int:
    """同步 game_records_v8/ → game_records_v8_kaggle/，返回同步文件数。"""
    if not src.is_dir():
        print(f"[ERROR] 源目录不存在: {src}")
        return 0

    dst.mkdir(parents=True, exist_ok=True)
    for old in dst.glob("*.json"):
        old.unlink()

    count = 0
    for fp in sorted(src.glob("*.json")):
        new_name = kaggle_filename(fp.name)
        shutil.copy2(fp, dst / new_name)
        count += 1

    return count


def write_metadata(dst: Path, title: str, dataset_id: str):
    """生成 dataset-metadata.json。"""
    meta = {
        "title": title,
        "id": dataset_id,
        "licenses": [{"name": "CC0-1.0"}],
        "isPrivate": False,
    }
    (dst / "dataset-metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def create_zip(dst: Path, zip_path: Path) -> int:
    """将 dst 目录下所有 JSON 打包为 zip（排除 metadata）。"""
    files = sorted(f for f in dst.glob("*.json") if "metadata" not in f.name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.name)
    return len(files)


def upload_via_cli(dataset_id: str, dst: Path):
    """通过 kaggle CLI 上传（需 ~/.kaggle/access_token）。

    注意：kaggle CLI 2.x 的 datasets create 有 KaggleObject.from_dict() bug，
    推荐使用 --zip 手动上传。此函数仅作为备选。
    """
    import subprocess
    import sys
    try:
        subprocess.run(["python", "-m", "kaggle", "--version"],
                       capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[ERROR] kaggle 未安装。运行: pip install kaggle")
        sys.exit(1)

    print(f"[INFO] 上传到: {dataset_id}")
    result = subprocess.run(
        ["python", "-m", "kaggle", "datasets", "create", "-p", str(dst)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"[OK] 上传成功")
    else:
        print(f"[ERROR] 上传失败: {result.stderr[:200]}")
        print("[TIP] CLI 有 bug，建议用 --zip 手动上传")


def main():
    parser = argparse.ArgumentParser(
        description="V8 Kaggle 数据同步（重命名 + zip + 上传）"
    )
    parser.add_argument("--zip", action="store_true",
                        help="打包 zip（手动上传用）")
    parser.add_argument("--upload", action="store_true",
                        help="CLI 上传（需 kaggle 凭证，有 bug 风险）")
    parser.add_argument("--title", default="Guandan V8 Records",
                        help="数据集标题（≤50 字符）")
    parser.add_argument("--dataset-id",
                        default="philsz/guandan-v8-game-records",
                        help="Kaggle 数据集 ID")
    parser.add_argument("--src", default=str(SRC_DIR))
    parser.add_argument("--dst", default=str(DST_DIR))
    args = parser.parse_args()

    src, dst = Path(args.src), Path(args.dst)

    # 1. 同步
    count = sync_records(src, dst)
    print(f"[OK] 同步完成: {count} 文件 → {dst}")

    # 2. 写 metadata
    write_metadata(dst, args.title, args.dataset_id)
    print(f"[OK] metadata: title={args.title}, id={args.dataset_id}")

    # 3. 打包 zip
    if args.zip:
        zip_path = PROJECT_ROOT / "_kaggle_data.zip"
        n = create_zip(dst, zip_path)
        size_kb = zip_path.stat().st_size / 1024
        print(f"[OK] ZIP: {zip_path.name} ({n} 文件, {size_kb:.0f} KB)")
        print()
        print("=== 手动上传步骤 ===")
        print(f"1. 打开 https://www.kaggle.com/datasets/new")
        print(f"2. 上传: {zip_path}")
        print(f"3. Title: {args.title}")
        print(f"4. License: CC0 (Public Domain)")

    # 4. CLI 上传
    if args.upload:
        upload_via_cli(args.dataset_id, dst)


if __name__ == "__main__":
    main()
