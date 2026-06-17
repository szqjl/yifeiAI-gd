#!/usr/bin/env python3
"""将本地 replay JSON 上传到 COS，并打印需写入 manifest 的 object_key / sha256。"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from cos_client import artifact_object_key, get_cos_client, load_env_file

REPO_ROOT = _SCRIPT_DIR.parents[1]
ENV_FILE = REPO_ROOT / "config" / "cos.env"
DEFAULT_PREFIX = "replays/regression-lalala-v1/"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    load_env_file(ENV_FILE)

    parser = argparse.ArgumentParser(description="上传单局 replay 到腾讯云 COS")
    parser.add_argument("file", type=Path, help="本地 JSON 路径")
    parser.add_argument("--id", dest="game_id", help="manifest 中的 id")
    parser.add_argument("--prefix", default=os.environ.get("COS_PREFIX", DEFAULT_PREFIX))
    args = parser.parse_args()

    client, bucket, _region = get_cos_client()

    src = args.file.resolve()
    if not src.is_file():
        print(f"文件不存在: {src}", file=sys.stderr)
        return 1

    game_id = args.game_id or src.stem
    prefix = args.prefix if args.prefix.endswith("/") else args.prefix + "/"
    object_key = artifact_object_key(f"{prefix}{src.name}")
    digest = sha256_file(src)

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
