#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Botzone 掼蛋在线 Bot 入口（__main__.py）。

打包后在 zip 根目录作为入口，Botzone 平台每回合调用一次（或 KEEP_RUNNING 长驻）。

协议（Botzone JSON Interaction）：
  stdin  一行 JSON: {"requests": [...], "responses": [...],
                     "data": ..., "globaldata": ...}
  stdout 一行 JSON: {"response": ..., "debug": ..., "data": ...}
  长驻模式：正常响应后再输出一行 >>>BOTZONE_REQUEST_KEEP_RUNNING<<< 并 flush，
  进程不退出，等待下一回合 stdin；引擎只加载一次（加载约 1.9s，冷启动必超时）。

决策链复用 src/communication/botzone_adapter.BotzoneAdapter：
  - ActionListGenerator / CardTracker / _classify_action / _beats / claim 构造
    与 Local AI 完全一致（同一套协议转换）。
  - 引擎 UltimateWinRateEngineV7(model=None)：规则栈 + 组牌，不依赖 torch
    运行时（torch 惰性导入，缺失时 model 恒 None）。

打包（scripts/launchers/botzone/package_v8_online.py）会复制 src/ 与
game_logic/ 等依赖，并将本文件放 zip 根。
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# zip 根（本文件所在目录）加入 path，保证 `src.*` 可导入。
# 本地运行时本文件位于 scripts/launchers/botzone/，src/ 在仓库根：
#  - 打包后（zip 根 / 解压目录）：__main__.py 与 src/ 同级 → ZIP_ROOT 即 src 所在；
#  - 仓库内本地运行：src/ 在仓库根（_REPO_ROOT = ZIP_ROOT.parents[3]）。
ZIP_ROOT = Path(__file__).resolve().parent
if str(ZIP_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIP_ROOT))

# 仓库根（本地运行 / 打包前自测用）：scripts/launchers/botzone → 仓库根
_REPO_ROOT = ZIP_ROOT.parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# 兼容 `python <xxx>.zip` 直接执行：此时 __file__ 形如 "<zip>/__main__.py"，
# parents[3] 无 src/，ZIP_ROOT（zip 包根）已含 src/，无需额外处理。

logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("v8_online")


def _load_engine():
    """加载 V8 决策引擎（model=None 规则栈 + 组牌；torch 可选）。"""
    from src.v.nn import UltimateWinRateEngineV7
    engine = UltimateWinRateEngineV7(player_id=0, use_grouping_engine=True)
    return engine


def _load_adapter(engine):
    from src.communication.botzone_adapter import BotzoneAdapter
    adapter = BotzoneAdapter(
        user_id="online", api_key="", decision_engine=engine, player_id=0,
    )
    return adapter


def main() -> int:
    import asyncio

    # 每回合调用一次，输出标准 JSON 响应 + KEEP_RUNNING 保持进程（加载一次引擎）。
    # 首回合加载引擎；后续回合复用已加载实例（进程常驻）。
    engine = None
    adapter = None

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
            logger.error("无法解析 stdin 输入: %s", line[:200])
            print(json.dumps({"response": json.dumps([[], []])}))
            sys.stdout.flush()
            continue

        if engine is None:
            engine = _load_engine()
            adapter = _load_adapter(engine)

        try:
            resp = asyncio.run(adapter.handle_online_turn(full_input))
        except Exception:
            logger.error("决策失败", exc_info=True)
            resp = json.dumps([[], []], separators=(",", ":"))

        # Botzone 在线输出：response 必须是 JSON 字符串（掼蛋响应本身是
        # [[action], [claim]] 数组的 JSON 序列化）。
        output = {
            "response": resp,
            "debug": "",
            "data": None,
            "globaldata": None,
        }
        print(json.dumps(output, separators=(",", ":")))
        sys.stdout.flush()

        # 长驻：保持进程等待下一回合；平台若按 restart 模式调用，此标记被忽略。
        print(">>>BOTZONE_REQUEST_KEEP_RUNNING<<<")
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
