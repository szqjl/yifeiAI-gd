"""腾讯云 COS 官方 Python SDK 封装（cos-python-sdk-v5）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / "config" / "cos.env"

if TYPE_CHECKING:
    from qcloud_cos import CosS3Client


def load_env_file(path: Path = ENV_FILE) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def get_cos_client() -> Tuple["CosS3Client", str, str]:
    """
    返回 (client, bucket, region)。
    使用官方 SDK：CosConfig + CosS3Client。
    文档：https://cloud.tencent.com/document/product/436/12269
    """
    load_env_file()

    secret_id = os.environ.get("COS_SECRET_ID")
    secret_key = os.environ.get("COS_SECRET_KEY")
    bucket = os.environ.get("COS_BUCKET")
    region = os.environ.get("COS_REGION", "ap-guangzhou")

    if not all([secret_id, secret_key, bucket]):
        print(
            "缺少 COS 配置。请：\n"
            "  1. cp config/cos.env.example config/cos.env\n"
            "  2. 填写 COS_SECRET_ID / COS_SECRET_KEY / COS_BUCKET\n"
            "  3. pip install cos-python-sdk-v5",
            file=sys.stderr,
        )
        raise SystemExit(1)

    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError:
        print(
            "未安装官方 SDK。请执行：pip install cos-python-sdk-v5\n"
            "产品文档：https://cloud.tencent.com/document/product/436/12269",
            file=sys.stderr,
        )
        raise SystemExit(1)

    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    return CosS3Client(config), bucket, region
