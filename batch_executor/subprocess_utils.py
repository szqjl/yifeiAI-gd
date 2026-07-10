"""批跑子进程输出捕获（Windows GBK 控制台兼容）。"""

from __future__ import annotations

import locale
import os
import subprocess
from typing import Mapping, MutableMapping, Sequence


def _decode_output(data: bytes | None) -> str:
    if not data:
        return ""
    for encoding in ("utf-8", locale.getpreferredencoding(False) or "utf-8", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def run_text_capture(
    cmd: Sequence[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    运行子进程并捕获文本输出。

    不使用 text=True，避免 Windows 下 GBK 控制台输出触发
    subprocess 内部 _readerthread 的 UnicodeDecodeError。
    """
    merged: MutableMapping[str, str] = dict(os.environ)
    if env:
        merged.update(env)
    merged.setdefault("PYTHONIOENCODING", "utf-8")

    result = subprocess.run(
        list(cmd),
        cwd=cwd,
        env=merged,
        capture_output=True,
    )
    return subprocess.CompletedProcess(
        args=result.args,
        returncode=result.returncode,
        stdout=_decode_output(result.stdout),
        stderr=_decode_output(result.stderr),
    )
