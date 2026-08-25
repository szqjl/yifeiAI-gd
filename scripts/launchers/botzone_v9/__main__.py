#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Botzone 掼蛋在线 Bot 入口 — V9 轻量 DMC（方案 A）。

与 V8（``scripts/launchers/botzone/__main__.py``）并存：
  - V8：UltimateWinRateEngineV7 规则栈 + 组牌
  - V9：NumPy DMC + V8 ActionListGenerator（``fd_v8_bridge`` 训练权重）

协议：Botzone JSON Interaction + KEEP_RUNNING 长驻。
权重：Botzone 用户存储 ``data/dmc_v9_weights.npz``（或 ``dmc_v8_bridge_A150.npz``）。
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ZIP_ROOT = Path(__file__).resolve().parent
if str(ZIP_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIP_ROOT))

_REPO_ROOT = ZIP_ROOT
if not (ZIP_ROOT / "src").exists():
    _cur = ZIP_ROOT
    while _cur != _cur.parent:
        if (_cur / "src").exists():
            _REPO_ROOT = _cur
            break
        _cur = _cur.parent
if _REPO_ROOT and str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("v9_dmc_online")

KEEP_RUNNING_LINE = ">>>BOTZONE_REQUEST_KEEP_RUNNING<<<"
_DECIDER = None


def _get_decider():
    global _DECIDER
    if _DECIDER is None:
        from src.v.nn.inference.dmc_botzone_decide import DmcBotzoneDecider
        _DECIDER = DmcBotzoneDecider()
        logger.warning("V9 DMC loaded: %s", _DECIDER.model_label)
    return _DECIDER


def _run_turn(full_input: dict) -> dict:
    decider = _get_decider()
    try:
        action = decider.handle_full_input(full_input)
    except Exception:
        logger.error("V9 决策失败", exc_info=True)
        action = [[], []]
    return {
        "response": action,
        "debug": f"V9-DMC model={decider.model_label}"[:1000],
        "data": None,
    }


def main() -> int:
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            full_input = json.loads(line)
        except json.JSONDecodeError:
            logger.error("stdin JSON 解析失败: %s", line[:200])
            print(json.dumps({"response": [[], []], "debug": "json_error", "data": None}))
            sys.stdout.flush()
            continue

        out = _run_turn(full_input)
        print(json.dumps(out, ensure_ascii=False))
        sys.stdout.flush()

        # 与 V8 一致：始终输出 KEEP_RUNNING，避免平台长驻模式下每回合冷启动
        print(KEEP_RUNNING_LINE)
        sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main() or 0)
