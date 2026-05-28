#!/usr/bin/env python3
"""按 manifest 从腾讯云 COS 拉取 regression-lalala-v1 对象到本地。"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "data" / "manifests" / "regression-lalala-v1.json"
ENV_FILE = REPO_ROOT / "config" / "cos.env"


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

    secret_id = os.environ.get("COS_SECRET_ID")
    secret_key = os.environ.get("COS_SECRET_KEY")
    bucket = os.environ.get("COS_BUCKET")
    region = os.environ.get("COS_REGION", "ap-guangzhou")
    local_dir = Path(
        os.environ.get(
            "COS_LOCAL_DIR",
            str(REPO_ROOT / "data" / "artifacts" / "replays" / "regression-lalala-v1"),
        )
    )

    if not all([secret_id, secret_key, bucket]):
        print(
            "缺少 COS 配置。请复制 config/cos.env.example → config/cos.env 并填写。\n"
            "或设置环境变量 COS_SECRET_ID / COS_SECRET_KEY / COS_BUCKET",
            file=sys.stderr,
        )
        return 1

    if not MANIFEST.is_file():
        print(f"未找到 manifest: {MANIFEST}", file=sys.stderr)
        return 1

    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError:
        print("请安装: pip install cos-python-sdk-v5", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    games = manifest.get("games") or []
    if not games:
        print("manifest 中 games 为空，请先登记对局或保留 placeholder 做连通性测试。", file=sys.stderr)
        return 1

    local_dir.mkdir(parents=True, exist_ok=True)
    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)

    ok, skip, fail = 0, 0, 0
    for game in games:
        key = game.get("object_key") or ""
        if not key or game.get("tags") == ["placeholder"]:
            print(f"[skip] {game.get('id', '?')}: placeholder 或未配置 object_key")
            skip += 1
            continue

        filename = Path(key).name
        dest = local_dir / filename
        expected = (game.get("sha256") or "").lower()

        print(f"[pull] cos://{bucket}/{key} -> {dest}")
        try:
            resp = client.get_object(Bucket=bucket, Key=key)
            body = resp["Body"].get_raw_stream().read()
            dest.write_bytes(body)
        except Exception as e:
            print(f"  [fail] {e}", file=sys.stderr)
            fail += 1
            continue

        if expected:
            actual = sha256_file(dest)
            if actual != expected:
                print(f"  [fail] sha256 不匹配: expected={expected[:12]}… actual={actual[:12]}…", file=sys.stderr)
                fail += 1
                continue
            print(f"  [ok] sha256 校验通过")
        else:
            print(f"  [ok] 已下载（manifest 未填 sha256，跳过校验）")
        ok += 1

    print(f"\n完成: ok={ok} skip={skip} fail={fail} -> {local_dir}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
