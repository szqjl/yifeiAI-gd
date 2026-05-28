#!/usr/bin/env python3
"""上传 game_records 中文件名含 szqjl 的 JSON 到 COS（默认 10 个）。"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from cos_client import artifact_object_key, get_cos_client, load_env_file

REPO_ROOT = _SCRIPT_DIR.parents[1]
ENV_FILE = REPO_ROOT / "config" / "cos.env"
GAME_RECORDS = REPO_ROOT / "game_records"
MANIFEST = REPO_ROOT / "data" / "manifests" / "szqjl-game-records-v1.json"
COS_PREFIX = "replays/szqjl-archive/"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def find_szqjl_files() -> list[Path]:
    if not GAME_RECORDS.is_dir():
        return []
    return sorted(
        p for p in GAME_RECORDS.glob("*.json") if "szqjl" in p.name.lower()
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    load_env_file(ENV_FILE)
    client, bucket, region = get_cos_client()

    files = find_szqjl_files()[: args.limit]
    if not files:
        print(
            f"未在 {GAME_RECORDS} 找到文件名含 szqjl 的 .json。\n"
            "请先放入记录，或运行 batch_update_szqjl_only.py 从 .rep 生成。",
            file=sys.stderr,
        )
        return 1

    prefix = COS_PREFIX if COS_PREFIX.endswith("/") else COS_PREFIX + "/"
    entries = []
    for i, src in enumerate(files, start=1):
        key = artifact_object_key(f"{prefix}{src.name}")
        digest = sha256_file(src)
        print(f"[szqjl-{i:03d}] {src.name} -> cos://{bucket}/{key}")
        with src.open("rb") as f:
            client.put_object(Bucket=bucket, Key=key, Body=f)
        entries.append(
            {
                "id": f"szqjl-{i:03d}",
                "object_key": key,
                "sha256": digest,
                "source": f"game_records/{src.name}",
                "added": date.today().isoformat(),
            }
        )

    manifest = {
        "schema_version": "1.0",
        "name": "szqjl-game-records-v1",
        "description": "文件名含 szqjl 的对局记录归档（非 regression 30 局集）",
        "storage": {
            "provider": "tencent_cos",
            "region": region,
            "bucket": bucket,
            "prefix": artifact_object_key(prefix.rstrip("/") + "/"),
        },
        "games": entries,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n完成: 上传 {len(entries)} 个 -> {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
