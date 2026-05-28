#!/usr/bin/env python3
"""将 COS 上整个 artifact 前缀同步到本地 data/artifacts/（单一网盘：一次拉齐）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / "config" / "cos.env"
DEFAULT_PREFIX = ""
DEFAULT_LOCAL = REPO_ROOT / "data" / "artifacts"


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    load_env_file(ENV_FILE)

    secret_id = os.environ.get("COS_SECRET_ID")
    secret_key = os.environ.get("COS_SECRET_KEY")
    bucket = os.environ.get("COS_BUCKET")
    region = os.environ.get("COS_REGION", "ap-guangzhou")
    prefix = os.environ.get("COS_ARTIFACT_PREFIX", DEFAULT_PREFIX)
    local_root = Path(os.environ.get("COS_ARTIFACT_LOCAL", str(DEFAULT_LOCAL)))

    if not all([secret_id, secret_key, bucket]):
        print("缺少 COS 配置，见 config/cos.env.example", file=sys.stderr)
        return 1

    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError:
        print("请安装: pip install cos-python-sdk-v5", file=sys.stderr)
        return 1

    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)
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
