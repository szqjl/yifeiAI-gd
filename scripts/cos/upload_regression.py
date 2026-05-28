#!/usr/bin/env python3
"""将本地 replay JSON 上传到 COS，并打印需写入 manifest 的 object_key / sha256。"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / "config" / "cos.env"
DEFAULT_PREFIX = "replays/regression-lalala-v1/"


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    load_env_file(ENV_FILE)

    parser = argparse.ArgumentParser(description="上传单局 replay 到腾讯云 COS")
    parser.add_argument("file", type=Path, help="本地 JSON 路径，如 game_records/xxx.json")
    parser.add_argument(
        "--id",
        dest="game_id",
        help="manifest 中的 id，默认用文件名（无扩展名）",
    )
    parser.add_argument("--prefix", default=os.environ.get("COS_PREFIX", DEFAULT_PREFIX))
    args = parser.parse_args()

    secret_id = os.environ.get("COS_SECRET_ID")
    secret_key = os.environ.get("COS_SECRET_KEY")
    bucket = os.environ.get("COS_BUCKET")
    region = os.environ.get("COS_REGION", "ap-guangzhou")

    if not all([secret_id, secret_key, bucket]):
        print("缺少 COS 配置，见 config/cos.env.example", file=sys.stderr)
        return 1

    src = args.file.resolve()
    if not src.is_file():
        print(f"文件不存在: {src}", file=sys.stderr)
        return 1

    game_id = args.game_id or src.stem
    prefix = args.prefix if args.prefix.endswith("/") else args.prefix + "/"
    object_key = f"{prefix}{src.name}"
    digest = sha256_file(src)

    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError:
        print("请安装: pip install cos-python-sdk-v5", file=sys.stderr)
        return 1

    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)

    print(f"[upload] {src} -> cos://{bucket}/{object_key}")
    with src.open("rb") as f:
        client.put_object(Bucket=bucket, Key=object_key, Body=f)

    print("\n--- 写入 manifest 的片段 ---")
    print(
        f'  "id": "{game_id}",\n'
        f'  "object_key": "{object_key}",\n'
        f'  "sha256": "{digest}",\n'
        f'  "tags": ["lalala"],\n'
        f'  "source": "{src.name}",'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
