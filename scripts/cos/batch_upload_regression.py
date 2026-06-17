#!/usr/bin/env python3
"""从 game_records 选取 yf1_m1 对局批量上传至 COS，并刷新 manifest。"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from cos_client import artifact_object_key, get_cos_client, load_env_file
from upload_regression import sha256_file

REPO_ROOT = _SCRIPT_DIR.parents[1]
ENV_FILE = REPO_ROOT / "config" / "cos.env"
MANIFEST = REPO_ROOT / "data" / "manifests" / "regression-lalala-v1.json"
GAME_RECORDS = REPO_ROOT / "game_records"
PREFIX = "replays/regression-lalala-v1/"


def game_id_from_name(name: str) -> str:
    m = re.match(r"^(\d+)", name)
    return m.group(1) if m else name


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="manifest 中总局数目标")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env_file(ENV_FILE)
    client, bucket, region = get_cos_client()
    artifact_root = __import__("os").environ.get("COS_ARTIFACT_PREFIX", "yifei-gd/").strip()
    if artifact_root and not artifact_root.endswith("/"):
        artifact_root += "/"

    files = sorted(p for p in GAME_RECORDS.glob("*.json") if "[yf1_m1]" in p.name)
    by_gid: dict[str, Path] = {}
    for p in files:
        gid = game_id_from_name(p.name)
        if gid not in by_gid:
            by_gid[gid] = p

    selected = list(by_gid.values())[: args.limit]
    if len(selected) < args.limit:
        print(f"警告: 仅找到 {len(selected)} 个不同 game_id 的 yf1_m1 文件", file=sys.stderr)

    games = []
    for i, src in enumerate(selected, start=1):
        reg_id = f"reg-{i:03d}"
        prefix = PREFIX if PREFIX.endswith("/") else PREFIX + "/"
        object_key = artifact_object_key(f"{prefix}{src.name}")
        digest = sha256_file(src)
        gid = game_id_from_name(src.name)

        print(f"[{reg_id}] upload {src.name}")
        if not args.dry_run:
            with src.open("rb") as f:
                client.put_object(Bucket=bucket, Key=object_key, Body=f)

        games.append(
            {
                "id": reg_id,
                "object_key": object_key,
                "sha256": digest,
                "tags": ["lalala", "yf1_m1"],
                "source": f"game_records/{src.name}",
                "game_id": gid,
                "added": date.today().isoformat(),
                "notes": "",
            }
        )

    manifest = {
        "schema_version": "1.0",
        "name": "regression-lalala-v1",
        "description": "M 系列对 lalala 固定回归集",
        "created": "2026-05-28",
        "game_count_target": 30,
        "storage": {
            "provider": "tencent_cos",
            "region": region,
            "bucket": bucket,
            "artifact_prefix": artifact_root,
            "prefix": artifact_object_key(PREFIX.rstrip("/") + "/"),
            "local_dir": "data/artifacts/replays/regression-lalala-v1",
            "docs": "docs/governance/COS-接入指南.md",
        },
        "games": games,
        "update_policy": {
            "max_replacements_per_rca_cycle": 5,
            "total_count_fixed": 30,
        },
    }

    if args.dry_run:
        print(json.dumps(manifest, ensure_ascii=False, indent=2)[:2000])
        return 0

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n完成: 上传 {len(games)} 局，已写入 {MANIFEST}")
    print("运行: python scripts/cos/pull_regression.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
