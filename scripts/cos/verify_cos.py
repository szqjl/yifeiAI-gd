#!/usr/bin/env python3
"""用腾讯云 COS 官方 Python SDK 验证 config/cos.env 是否可用。"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from cos_client import get_cos_client


def main() -> int:
    client, bucket, region = get_cos_client()
    prefix = __import__("os").environ.get("COS_ARTIFACT_PREFIX", "")

    print(f"SDK: cos-python-sdk-v5 (官方)")
    print(f"Region: {region}")
    print(f"Bucket: {bucket}")
    print(f"Prefix: {prefix or '(桶根)'}")

    try:
        client.head_bucket(Bucket=bucket)
        print("[ok] head_bucket 成功，桶可访问")
    except Exception as e:
        print(f"[fail] head_bucket: {e}", file=sys.stderr)
        return 1

    try:
        resp = client.list_objects(Bucket=bucket, Prefix=prefix, MaxKeys=5)
        keys = [o["Key"] for o in (resp.get("Contents") or [])]
        print(f"[ok] list_objects 成功，样例 key 数量: {len(keys)}")
        for k in keys:
            print(f"  - {k}")
        if not keys:
            print("  （前缀下暂无对象，上传一局 replay 后可见）")
    except Exception as e:
        print(f"[fail] list_objects: {e}", file=sys.stderr)
        return 1

    print("\nCOS 配置正常。下一步：")
    print("  python scripts/cos/upload_regression.py <replay.json> --id reg-001")
    return 0


if __name__ == "__main__":
    sys.exit(main())
