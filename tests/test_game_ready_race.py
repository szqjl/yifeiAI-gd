# -*- coding: utf-8 -*-
"""
GUA-049 game_ready.json 多进程并发写盘 race condition 测试

根因：`batch_executor/client_ready.py:231` 的 `_game_save` 使用
`Path.write_text` 非原子写。`_game_load` 与 `_game_save` 之间的
check-modify-write 窗口在 4 进程并发下会产生：
  1) JSON 文件被截断/交错（`Expecting ',' delimiter` 解析错误）
  2) entry 互相覆盖丢失（4 个 client_id 写入后只保留 1-3 个）

本测试用 `multiprocessing.Pool(4)` 模拟 4 进程并发（绕过 GIL，
比 threading 更接近真实多客户端场景），跑 100 轮统计损坏/丢失次数。

注意：
  - 不修改源文件 `_game_save`；用本文件内复制的对照实现做测试
  - Windows / WSL 下 `multiprocessing` 需要 `if __name__ == "__main__":` 保护
  - 每个轮次使用独立临时目录，避免文件级锁影响下一轮
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

import pytest


# ────────────────────────────────────────────────────────────
# 待测逻辑：原版（非原子）和对照版（原子）
# ────────────────────────────────────────────────────────────

# 复制自 batch_executor/client_ready.py 的原版实现（不修改源文件）
# 这是 GUA-049 出问题的函数
def _game_save_original(game_ready_file: Path, data: Dict[str, dict]) -> None:
    """原版：非原子 write_text — 多进程下会产生 race condition。"""
    game_ready_file.parent.mkdir(parents=True, exist_ok=True)
    game_ready_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _game_load(game_ready_file: Path) -> Dict[str, dict]:
    """原版 _game_load 的最小复刻。"""
    if not game_ready_file.exists():
        return {}
    try:
        raw = game_ready_file.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        d = json.loads(raw)
        return d if isinstance(d, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


# 修复版：tmp file + os.replace 原子替换（参考 POSIX rename 原子语义）
def _game_save_atomic(game_ready_file: Path, data: Dict[str, dict]) -> None:
    """修复版：先写临时文件，再原子替换。
    关键：临时文件名必须 per-worker 唯一，否则多个 worker 会写同一个
    .tmp 文件，第二个 write_text 会覆盖第一个，或 os.replace 时源文件
    已被另一个 worker 替换走。
    Windows 上 os.replace 偶尔会被 AV/索引器临时锁目标文件，
    所以加一个小重试循环。
    """
    game_ready_file.parent.mkdir(parents=True, exist_ok=True)
    # 用 PID + 微秒时间戳保证唯一性
    tmp_name = f"{game_ready_file.name}.{os.getpid()}.{time.time_ns()}.tmp"
    tmp = game_ready_file.parent / tmp_name
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # 重试：Windows 偶发 WinError 5/32（AV 扫描/索引器短占目标）
    last_err: Exception | None = None
    for _attempt in range(20):
        try:
            os.replace(tmp, game_ready_file)
            return
        except PermissionError as e:  # Windows only
            last_err = e
            time.sleep(0.01)
    # 走到这里说明真的拿不到，重抛
    if last_err is not None:
        raise last_err


# ────────────────────────────────────────────────────────────
# 进程入口：必须是模块级（picklable），每个 worker 写自己的 client_id
# ────────────────────────────────────────────────────────────

# 4 个固定的 client_id（按批跑约定的四席）
CLIENT_IDS: Tuple[str, ...] = ("yf1_v7", "client3", "yf2_v7", "client4")


def _worker_legacy(args: Tuple[str, str, int]) -> None:
    """原版 _game_save 的多进程 worker：load → modify → save。"""
    game_ready_file, client_id, _round = args
    path = Path(game_ready_file)
    data = _game_load(path)
    # 模拟真实场景中"修改 data"需要的时间（数据校验、字段拼装等），
    # 拉大 read 与 write 之间的窗口，让 race condition 更容易复现
    time.sleep(0.02)
    data[client_id] = {"ready": True, "timestamp": f"2026-06-07T00:00:0{_round}"}
    _game_save_original(path, data)


def _worker_atomic(args: Tuple[str, str, int]) -> None:
    """修复版 _game_save 的多进程 worker。"""
    game_ready_file, client_id, _round = args
    path = Path(game_ready_file)
    data = _game_load(path)
    time.sleep(0.02)
    data[client_id] = {"ready": True, "timestamp": f"2026-06-07T00:00:0{_round}"}
    _game_save_atomic(path, data)


def _worker_mark_game_ready(args: Tuple[str, str, int]) -> None:
    """端到端：模拟 mark_game_ready 的 4 进程并发。"""
    game_ready_file, client_id, _round = args
    path = Path(game_ready_file)
    data = _game_load(path)
    time.sleep(0.02)
    data[client_id] = {"ready": True, "timestamp": f"2026-06-07T00:00:0{_round}"}
    # 用原子写，验证端到端在修复版下也稳
    _game_save_atomic(path, data)


# ────────────────────────────────────────────────────────────
# 评估函数
# ────────────────────────────────────────────────────────────

def _inspect_final_file(game_ready_file: Path) -> Tuple[bool, int]:
    """返回 (json_ok, entry_count)。"""
    if not game_ready_file.exists():
        return False, 0
    try:
        raw = game_ready_file.read_text(encoding="utf-8").strip()
        if not raw:
            return True, 0  # 空文件本身是合法 JSON
        data = json.loads(raw)
        if not isinstance(data, dict):
            return False, 0
        return True, len(data)
    except (json.JSONDecodeError, OSError):
        return False, 0


def _run_concurrent_rounds(
    save_fn,
    rounds: int = 100,
    n_workers: int = 4,
) -> Tuple[int, int, int]:
    """
    跑 rounds 轮并发写盘；每轮用独立临时目录。
    返回 (损坏轮次数, 4entry全在的轮次数, 总轮次数)。
    """
    corrupted_rounds = 0
    intact_rounds_with_all_entries = 0

    for r in range(rounds):
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"gua049_r{r}_"))
        try:
            game_ready_file = tmp_dir / "game_ready.json"
            # 预置空文件（与 _game_load 在文件不存在时返回 {} 等价）
            game_ready_file.write_text("{}", encoding="utf-8")

            tasks = [(str(game_ready_file), cid, r) for cid in CLIENT_IDS]
            with mp.Pool(processes=n_workers) as pool:
                pool.map(save_fn, tasks)

            ok, count = _inspect_final_file(game_ready_file)
            if not ok:
                corrupted_rounds += 1
            elif count == len(CLIENT_IDS):
                intact_rounds_with_all_entries += 1
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return corrupted_rounds, intact_rounds_with_all_entries, rounds


# ────────────────────────────────────────────────────────────
# 测试用例
# ────────────────────────────────────────────────────────────

class TestGameReadyRace:
    """GUA-049 race condition 多进程验证（测试源文件 _game_save 不动）。"""

    def test_01_reproduce_race_4_process_100_rounds(self):
        """
        测试 1：4 进程并发调原版（非原子）_game_save，跑 100 轮。

        预期：race condition 必有迹可循——JSON 损坏或 entry 缺失总数 > 5
        （任意 100 轮至少 5 轮以上 race 表现）。这是 race condition 存在的硬证据。

        复现发现（2026-06-07 WSL）：损坏=1 缺失=86，二者都是 race 表现。
        Windows 下损坏/缺失概率会显著更高（文件锁/AV/索引服务干扰）。
        """
        corrupted, intact, total = _run_concurrent_rounds(
            _worker_legacy, rounds=100, n_workers=4
        )
        missing_rounds = total - intact  # entry 缺失轮次 = 损坏轮次 (含损坏的) + 损坏以外的缺失
        # "race 总表现" = 损坏轮次 + entry 缺失轮次
        # 注: 损坏轮次在 missing_rounds 里已计（损坏 ⇒ not intact），需去重
        # missing_rounds 已经把 corrupted 也计进去（损坏 ⇒ 0 entry ⇒ not intact）
        race_evidence = missing_rounds  # 损坏 + 不完整 entry 数

        # 报告统计（pytest -s 可见）
        print(
            f"\n[TEST 1] 4进程 × 100轮: 损坏={corrupted} "
            f"完整4entry={intact}/{total} race_evidence={race_evidence}"
        )

        # 核心断言：race 存在 → race_evidence > 5
        # 注：损坏或缺失都是 race；Linux/WSL 下损坏少、缺失多；Windows 下两者都多
        assert race_evidence > 5, (
            f"100 轮中 race 表现仅 {race_evidence}（损坏={corrupted}, 4entry 完整={intact}/{total}），"
            f"未达到 > 5 阈值；race condition 复现失败"
        )

    def test_02_atomic_fix_yields_zero_corruption(self):
        """
        测试 2：4 进程并发调原子版 _game_save（tmp + os.replace），跑 100 轮。

        预期：
        - JSON 损坏 == 0（原子写消除损坏中间态）
        - 4 entry 完整率 > 非原子版（read-modify-write 并发覆盖仍可能丢 entry）

        复现发现（2026-06-07 WSL）：原子版 5/100 完整 vs 非原子版 4/100 完整——
        **tmp+replace 解决 JSON 损坏但没解决 read-modify-write 覆盖**。
        真正修法见报告 §5.4：fcntl/msvcrt 文件锁 / SQLite / 单一 writer 进程。
        """
        corrupted, intact, total = _run_concurrent_rounds(
            _worker_atomic, rounds=100, n_workers=4
        )

        print(
            f"\n[TEST 2] 4进程 × 100轮 atomic: 损坏={corrupted} "
            f"完整4entry={intact}/{total}"
        )

        # 原子写应消除 JSON 损坏中间态
        assert corrupted == 0, (
            f"原子写后仍出现 {corrupted} 轮 JSON 损坏，"
            f"修复方案未生效"
        )
        # 原子写不解决 read-modify-write 并发覆盖，intact 比例无强保证
        # 仅保证 0 损坏（这才是 tmp+replace 原子写的真正能力边界）
        # 注：完整 4 entry 需 read-modify-write 加锁才能保证

    def test_03_mark_game_ready_endtoend(self):
        """
        测试 3：4 进程并发模拟 mark_game_ready 端到端，跑 100 轮（用原子写）。

        预期：
        - JSON 损坏 == 0（原子写保证）
        - 4 entry 完整率无强保证（read-modify-write 仍并发覆盖）

        复现发现（2026-06-07 WSL）：完整 4 entry = 2/100，远低于预期。
        真正修法见报告 §5.4。
        """
        corrupted, intact, total = _run_concurrent_rounds(
            _worker_mark_game_ready, rounds=100, n_workers=4
        )

        print(
            f"\n[TEST 3] mark_game_ready × 100轮: 损坏={corrupted} "
            f"完整4entry={intact}/{total}"
        )

        # 端到端：JSON 损坏 == 0（原子写保证）
        assert corrupted == 0
        # 注：intact 比例无强保证，read-modify-write 加锁才能 100%
        # 此测试用于发现"原子写不能解决并发覆盖"问题，不作关单硬指标

    def test_04_file_lock_fixes_rmw_race(self):
        """
        测试 4：4 进程并发 + 文件锁（fcntl/msvcrt）跑 20 轮。
        预期：损坏 == 0 且 4 entry 完整 == 20。
        修复版 worker 用 advisory 文件锁包住 read-modify-write 全段。
        Windows 文件锁争用比纯原子写慢 10x+；20 轮够用。
        """
        if not (_HAS_FCNTL or _HAS_MSVCRT):
            pytest.skip("本平台无文件锁支持 (fcntl/msvcrt)")

        corrupted, intact, total = _run_concurrent_rounds(
            _worker_with_lock, rounds=20, n_workers=4
        )

        print(
            f"\n[TEST 4] 4进程×20轮 文件锁版: 损坏={corrupted} "
            f"完整4entry={intact}/{total}"
        )

        assert corrupted == 0
        assert intact == total

    def test_05_real_source_mark_game_ready(self, monkeypatch, tmp_path):
        """
        测试 5：直接调用源码 mark_game_ready，验证 try/except + 原子写。
        """
        import batch_executor.client_ready as cr

        monkeypatch.setattr(cr, "GAME_READY_FILE", tmp_path / "game_ready.json")
        monkeypatch.setattr(cr, "READY_FILE", tmp_path / "clients_ready.json")

        cr.clear_all_ready()
        for cid in ("yf1_v7", "yf2_v7", "client3", "client4"):
            cr.mark_game_ready(cid)

        data = json.loads(crp(cr, tmp_path))
        assert set(data.keys()) == {"yf1_v7", "yf2_v7", "client3", "client4"}
        for entry in data.values():
            assert entry["ready"] is True
            assert "timestamp" in entry

    def test_06_mark_game_ready_logs_exceptions(self, monkeypatch, caplog, tmp_path):
        """
        测试 6（P1 修复门禁）：mark_game_ready 内部异常应被 logger 记录，不应静默。
        当前源码 mark_game_ready 尚无 try/except，本测试预期 fail。
        修 P1（在 mark_game_ready 加 try/except + logger）后本测试应 pass。
        """
        import logging

        import batch_executor.client_ready as cr

        monkeypatch.setattr(cr, "GAME_READY_FILE", tmp_path / "game_ready.json")

        def _boom(_data):
            raise OSError("simulated disk full")

        monkeypatch.setattr(cr, "_game_save", _boom)

        with caplog.at_level(logging.ERROR, logger="client_ready"):
            with pytest.raises(OSError, match="simulated disk full"):
                cr.mark_game_ready("yf1_v7")

        assert any("simulated disk full" in rec.message for rec in caplog.records), (
            "P1 未修：mark_game_ready 异常未通过 logger 暴露；"
            "应在函数体内 try/except + logging.getLogger('client_ready').error"
        )


# ────────────────────────────────────────────────────────────
# P0 修复版：文件锁（fcntl/msvcrt）包住 read-modify-write
# ────────────────────────────────────────────────────────────

_HAS_FCNTL = hasattr(__import__("os"), "fcntl")
_HAS_MSVCRT = False
try:
    import msvcrt  # type: ignore[import-not-found]
    _HAS_MSVCRT = True
except ImportError:
    pass


def _lock_acquire(fh) -> bool:
    """非阻塞获取文件锁；获取成功返回 True，超时/失败返回 False。"""
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
    return True  # no lock support


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


def _game_load_save_locked(game_ready_file: Path, new_data: Dict[str, dict]) -> None:
    """带文件锁的 read-modify-write（带超时重试，避免无限等待）。"""
    lock_path = game_ready_file.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 5.0  # 5s 总超时
    while True:
        with open(lock_path, "a+", encoding="utf-8") as lf:
            if _lock_acquire(lf):
                try:
                    if game_ready_file.exists():
                        try:
                            raw = game_ready_file.read_text(encoding="utf-8").strip()
                            data = json.loads(raw) if raw else {}
                        except (json.JSONDecodeError, OSError):
                            data = {}
                    else:
                        data = {}
                    data.update(new_data)
                    tmp_name = f"{game_ready_file.name}.{os.getpid()}.{time.time_ns()}.tmp"
                    tmp = game_ready_file.parent / tmp_name
                    tmp.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    for _ in range(20):
                        try:
                            os.replace(tmp, game_ready_file)
                            break
                        except PermissionError:
                            time.sleep(0.01)
                    return
                finally:
                    _lock_release(lf)
        if time.monotonic() > deadline:
            raise TimeoutError("file lock acquire timeout after 5s")
        time.sleep(0.005)


def _worker_with_lock(args: Tuple[str, str, int]) -> None:
    """P0 修复版 worker：文件锁 + 原子写。"""
    game_ready_file, client_id, _round = args
    _game_load_save_locked(
        Path(game_ready_file),
        {client_id: {"ready": True, "timestamp": f"2026-06-07T00:00:0{_round}"}},
    )


def crp(cr, tmp_path) -> str:
    """读 GAME_READY_FILE 文本。"""
    return (tmp_path / "game_ready.json").read_text(encoding="utf-8")


if __name__ == "__main__":
    # Windows / WSL 下 multiprocessing 必须有 main 保护
    pytest.main([__file__, "-v", "-s"])
