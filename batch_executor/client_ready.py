# -*- coding: utf-8 -*-
"""批跑四席 WebSocket 就绪登记：确保按序连入且末席连上后再开局。"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# 跨平台文件锁（fcntl Linux / msvcrt Windows）
_HAS_FCNTL = hasattr(os, "fcntl")
_HAS_MSVCRT = False
try:
    import msvcrt  # type: ignore[import-not-found]
    _HAS_MSVCRT = True
except ImportError:
    pass

READY_FILE = Path(__file__).resolve().parent / "clients_ready.json"
GAME_READY_FILE = Path(__file__).resolve().parent / "game_ready.json"

# 连接顺序（0=首席直连，末席连上后平台自动开局）
CONNECT_ORDER_INDEX: Dict[str, int] = {
    "yf1_v7": 0,
    "yf1_m1": 0,
    "yf1_m3": 0,
    "yf1_v8": 0,
    "client3": 1,
    "yf3_v8": 1,
    "yf2_v7": 2,
    "yf2_m1": 2,
    "yf2_m3": 2,
    "yf2_v8": 2,
    "client4": 3,
    "yf4_v8": 3,
}

# 末席（client4）连入前额外稳定等待（秒）；平台第 4 席 WS 连上即开局
SETTLE_BEFORE_LAST_CONNECT = 7.0

YF1_CLIENT_IDS = frozenset({"yf1_v7", "yf1_m1", "yf1_m3", "yf1_v8"})
YF2_CLIENT_IDS = frozenset({"yf2_v7", "yf2_m1", "yf2_m3", "yf2_v8"})
YF3_CLIENT_IDS = frozenset({"yf3_v8"})
YF4_CLIENT_IDS = frozenset({"yf4_v8"})


def _now_iso() -> str:
    return datetime.now().isoformat()


def _lock_acquire(fh) -> bool:
    if _HAS_FCNTL:
        import fcntl
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (BlockingIOError, OSError):
            return False
    elif _HAS_MSVCRT:
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    return True


def _lock_release(fh) -> None:
    if _HAS_FCNTL:
        import fcntl
        try:
            fcntl.flock(fh, fcntl.LOCK_UN)
        except OSError:
            pass
    elif _HAS_MSVCRT:
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass


def clear_all_ready() -> None:
    """新批次开始前清空就绪表（原子写）。"""
    _atomic_write(READY_FILE, "{}")
    _atomic_write(GAME_READY_FILE, "{}")


def _atomic_write(file_path: Path, content: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = f"{file_path.name}.{os.getpid()}.{time.time_ns()}.tmp"
    tmp = file_path.parent / tmp_name
    tmp.write_text(content, encoding="utf-8")
    for _ in range(20):
        try:
            os.replace(tmp, file_path)
            return
        except PermissionError:
            time.sleep(0.01)
    os.replace(tmp, file_path)


def _locked_read_modify_write(file_path: Path, update_fn) -> None:
    """带文件锁的 read-modify-write（原子写 + 跨进程互斥）。"""
    lock_path = file_path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 5.0
    while True:
        with open(lock_path, "a+", encoding="utf-8") as lf:
            if _lock_acquire(lf):
                try:
                    if file_path.exists():
                        try:
                            raw = file_path.read_text(encoding="utf-8").strip()
                            data = json.loads(raw) if raw else {}
                        except (json.JSONDecodeError, OSError):
                            data = {}
                    else:
                        data = {}
                    update_fn(data)
                    content = json.dumps(data, ensure_ascii=False, indent=2)
                    tmp_name = f"{file_path.name}.{os.getpid()}.{time.time_ns()}.tmp"
                    tmp = file_path.parent / tmp_name
                    tmp.write_text(content, encoding="utf-8")
                    for _ in range(20):
                        try:
                            os.replace(tmp, file_path)
                            break
                        except PermissionError:
                            time.sleep(0.01)
                    return
                finally:
                    _lock_release(lf)
        if time.monotonic() > deadline:
            raise TimeoutError(f"file lock acquire timeout after 5s: {file_path}")
        time.sleep(0.005)


def mark_client_ready(client_id: str) -> None:
    """客户端 WebSocket 连上后登记。"""
    data = _load()
    data[client_id] = {"connected": True, "timestamp": _now_iso()}
    _save(data)


def mark_game_ready(client_id: str) -> None:
    """客户端收到首条游戏消息后登记（游戏已开局，客户端可正常决策）。"""
    data = _game_load()
    data[client_id] = {"ready": True, "timestamp": _now_iso()}
    _game_save(data)


def unmark_client_ready(client_id: str) -> None:
    data = _load()
    data.pop(client_id, None)
    _save(data)


def get_ready_clients() -> Dict[str, dict]:
    return _load()


def count_ready() -> int:
    return len(_load())


def is_client_ready(client_id: str) -> bool:
    return client_id in _load()


def client_id_from_script(script_path: str) -> Optional[str]:
    """从批跑脚本路径推断平台 user_info。"""
    name = Path(script_path).stem.lower()
    if name == "run_lalala_client3":
        return "client3"
    if name == "run_lalala_client4":
        return "client4"
    if name.startswith("yf1_"):
        return Path(script_path).stem
    if name.startswith("yf2_"):
        return Path(script_path).stem
    if name.startswith("yf3_"):
        return Path(script_path).stem
    if name.startswith("yf4_"):
        return Path(script_path).stem
    return None


def _peers_ready(client_id: str, ready: Dict[str, dict]) -> bool:
    """按席位身份判断前序是否已登记（不用纯计数，避免错序误判）。"""
    keys = set(ready.keys())
    if client_id == "client3":
        return bool(keys & YF1_CLIENT_IDS)
    if client_id in YF2_CLIENT_IDS:
        return bool(keys & YF1_CLIENT_IDS) and ("client3" in keys or bool(keys & YF3_CLIENT_IDS))
    if client_id == "client4":
        return (
            bool(keys & YF1_CLIENT_IDS)
            and "client3" in keys
            and bool(keys & YF2_CLIENT_IDS)
        )
    if client_id in YF3_CLIENT_IDS:
        return bool(keys & YF1_CLIENT_IDS)
    if client_id in YF4_CLIENT_IDS:
        return bool(keys & (YF1_CLIENT_IDS | YF3_CLIENT_IDS)) and bool(keys & YF2_CLIENT_IDS)
    return True


def wait_for_connect_turn(
    client_id: str,
    *,
    timeout: float = 120.0,
    poll_interval: float = 0.5,
) -> bool:
    """
    按连接顺位等待前序席位就绪后再连 WS。
    返回 False 表示超时（调用方应中止连入）。
    """
    if os.environ.get("YF_SKIP_CONNECT_GATE", "").strip() in ("1", "true", "yes"):
        return True

    order = CONNECT_ORDER_INDEX.get(client_id)
    if order is None or order <= 0:
        return True

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready = _load()
        if _peers_ready(client_id, ready):
            if order == 3:
                print(
                    f"[{client_id}] 前三席已就绪，稳定等待 "
                    f"{SETTLE_BEFORE_LAST_CONNECT:.0f}s 后连接（第4席连上即开局）",
                    flush=True,
                )
                time.sleep(SETTLE_BEFORE_LAST_CONNECT)
            return True
        time.sleep(poll_interval)

    return False


def wait_for_all_clients(
    expected_ids: Iterable[str],
    *,
    timeout: float = 90.0,
    poll_interval: float = 1.0,
    stable_seconds: float = 2.0,
    stable_checks: int = 2,
) -> bool:
    """批跑侧等待 expected_ids 全部登记就绪。"""
    expected = list(expected_ids)
    if not expected:
        return True

    deadline = time.monotonic() + timeout
    stable_start: Optional[float] = None
    consecutive = 0

    while time.monotonic() < deadline:
        ready = _load()
        missing = [cid for cid in expected if cid not in ready]
        if not missing:
            if stable_start is None:
                stable_start = time.monotonic()
                consecutive = 1
            else:
                consecutive += 1
            if (
                consecutive >= stable_checks
                and (time.monotonic() - stable_start) >= stable_seconds
            ):
                return True
        else:
            stable_start = None
            consecutive = 0
        time.sleep(poll_interval)

    return False


def wait_for_all_clients_game_ready(
    expected_ids: Iterable[str],
    *,
    timeout: float = 90.0,
    poll_interval: float = 1.0,
) -> bool:
    """批跑侧等待 expected_ids 全部 game_ready（首条游戏消息已被处理）。"""
    expected = set(expected_ids)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready = _game_load()
        if expected.issubset(ready.keys()):
            return True
        time.sleep(poll_interval)
    return False


def _load() -> Dict[str, dict]:
    if not READY_FILE.exists():
        return {}
    try:
        raw = READY_FILE.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: Dict[str, dict]) -> None:
    _locked_read_modify_write(READY_FILE, lambda d: d.update(data))


def _game_load() -> Dict[str, dict]:
    if not GAME_READY_FILE.exists():
        return {}
    try:
        raw = GAME_READY_FILE.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _game_save(data: Dict[str, dict]) -> None:
    _locked_read_modify_write(GAME_READY_FILE, lambda d: d.update(data))
