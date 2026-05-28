#!/usr/bin/env python3
"""将 COS 上整个 artifact 前缀同步到本地 data/artifacts/。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from cos_client import get_cos_client, load_env_file

REPO_ROOT = _SCRIPT_DIR.parents[1]
ENV_FILE = REPO_ROOT / "config" / "cos.env"
DEFAULT_PREFIX = ""
DEFAULT_LOCAL = REPO_ROOT / "data" / "artifacts"


def main() -> int:
    load_env_file(ENV_FILE)
    client, bucket, _region = get_cos_client()
    prefix = os.environ.get("COS_ARTIFACT_PREFIX", DEFAULT_PREFIX)
    local_root = Path(os.environ.get("COS_ARTIFACT_LOCAL", str(DEFAULT_LOCAL)))

    local_root.mkdir(parents=True, exist_ok=True)
    marker = ""
    count = 0
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
        if marker:
            kwargs["Marker"] = marker
        resp = client.list_objects(**kwargs)
        contents = resp.get("Contents") or []
        for obj in contents:
            key = obj["Key"]
            if key.endswith("/"):
                continue
            rel = key[len(prefix) :] if prefix and key.startswith(prefix) else key
            dest = local_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            print(f"[pull] {key} -> {dest}")
            body = client.get_object(Bucket=bucket, Key=key)["Body"].get_raw_stream().read()
            dest.write_bytes(body)
            count += 1
        if resp.get("IsTruncated") == "true":
            marker = resp.get("NextMarker") or (contents[-1]["Key"] if contents else "")
        else:
            break

    print(f"\n完成: 共下载 {count} 个对象 -> {local_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
