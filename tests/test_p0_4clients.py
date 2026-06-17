#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 改进验证脚本 - 完整 4 客户端版本

修复点（相比旧的 test_p0_correct.py / test_p0_single_game.py）：
  1. 离线平台 v1006 必须连满 4 个客户端才会自动开始游戏（PDF 第 2 页明文规定：
     "连满4人之后游戏将自动开始，即在连入client4.py之后将自动开始"）。
     旧脚本只启动 yf1_m1 + yf2_m1 两个客户端，导致平台一直在等剩余 2 个连入，
     永远不发 act/play 出牌请求。
  2. 监听平台 stdout，等待 "Ready for connect." 信号后再依次启动 4 个客户端。
  3. 游戏运行期间不杀客户端进程（不 sleep+terminate 截断），改为等待平台进程
     自然结束（指定 N 局打完即 gameOver），最长超时兜底。
  4. 平台进程退出后再读最新日志，避免读到不完整文件。

座位分配（PDF 第 2 页：第1+第3连接为一队，第2+第4一队）：
  连接 1 (pos 0) → yf1_m1                           [我方]
  连接 2 (pos 1) → run_lalala_client3               [对手]
  连接 3 (pos 2) → yf2_m1                           [我方]
  连接 4 (pos 3) → run_lalala_client4               [对手]
"""

import os
import sys
import time
import threading
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
PLATFORM_EXE = PROJECT_DIR / "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"

# 关键：必须用 python.exe（Python 3.13，已装齐 websockets/psutil/torch），
# 不能用 sys.executable（如果脚本被 py.exe → Python 3.14 启动，client 会因
# 缺 websockets 而立即 ModuleNotFoundError 崩溃）。
def _resolve_python():
    import shutil
    candidate = shutil.which("python")
    if candidate and "Python313" in candidate:
        return candidate
    # 兜底：直接走已知绝对路径
    fixed = Path(r"C:\Users\Jennifer\AppData\Local\Programs\Python\Python313\python.exe")
    if fixed.exists():
        return str(fixed)
    if candidate:
        return candidate
    return sys.executable

PYTHON_EXE = _resolve_python()

# 客户端按连接顺序排列（连接顺序决定座位号 0,1,2,3）
CLIENTS = [
    ("yf1_m1",        PROJECT_DIR / "src/communication/yf1_m1.py"),
    ("lalala_client3", PROJECT_DIR / "src/communication/run_lalala_client3.py"),
    ("yf2_m1",        PROJECT_DIR / "src/communication/yf2_m1.py"),
    ("lalala_client4", PROJECT_DIR / "src/communication/run_lalala_client4.py"),
]

NUM_GAMES = 30                        # ⚠️ 平台单位不是局数（30→实际跑约 20 局），见 memory platform-num-games-not-round-count
PLATFORM_READY_TIMEOUT = 30           # 等 "Ready for connect." 的最长时间
GAME_RUN_TIMEOUT = 180                # 平台完成 NUM_GAMES 后只空转不退出，120~180s 足够兜底
# 注意：yf1_m1 / yf2_m1 启动重（import torch 等），实际从进程启动到调用 connect()
# 内部 time.sleep 之后建立 WS 连接需要 ~10s。client3/client4 启动很轻。
# 因此外部启动间隔必须大于 yf 内部 import+sleep 的总耗时，否则连接顺序会乱。
PER_CLIENT_LAUNCH_GAP = 10            # 与 batch_executor (3s) 不同，这里更保守

# 每个客户端的 stdout/stderr 单独捕获，便于事后诊断
DIAG_DIR = PROJECT_DIR / "logs" / "test_p0_4clients_stdout"


def kill_residual_processes():
    """清理上一次残留的平台进程，避免端口 23456 占用。"""
    # 通过 cmd 执行 taskkill，绕过 git-bash 对 /F 的路径解析问题
    subprocess.run(
        ["cmd", "/c", "taskkill /F /IM guandan_offline_v1006.exe"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)


def monitor_platform_output(proc, ready_event, stop_event, sink_lines):
    """读平台 stdout：捕获 'Ready for connect.' 触发 event；同时把行追加到 sink。"""
    try:
        for line in iter(proc.stdout.readline, ''):
            if stop_event.is_set():
                break
            if not line:
                break
            line = line.rstrip()
            sink_lines.append(line)
            print(f"[PLATFORM] {line}")
            if "Ready for connect" in line and not ready_event.is_set():
                ready_event.set()
    except Exception as e:
        print(f"[ERROR] 平台输出监听异常: {e}")


def launch_client(name, script_path):
    """启动单个客户端，stdout/stderr 重定向到独立日志文件（便于事后诊断）。"""
    if not script_path.exists():
        print(f"[ERROR] 客户端脚本不存在: {script_path}")
        return None
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIAG_DIR / f"{name}.out.log"
    out_f = open(out_path, "w", encoding="utf-8", errors="replace")
    print(f"[CLIENT] 启动 {name}: {script_path}  → {out_path.name}")
    return subprocess.Popen(
        [PYTHON_EXE, "-u", str(script_path)],
        cwd=str(PROJECT_DIR),
        stdout=out_f,
        stderr=subprocess.STDOUT,
    )


def main():
    os.chdir(PROJECT_DIR)

    if not PLATFORM_EXE.exists():
        print(f"[FATAL] 平台 exe 不存在: {PLATFORM_EXE}")
        return 2

    print("[STEP 1/5] 清理残留进程...")
    kill_residual_processes()

    print(f"[STEP 2/5] 启动平台: {PLATFORM_EXE.name} {NUM_GAMES} (用 {PYTHON_EXE} 启动客户端)")
    platform_proc = subprocess.Popen(
        [str(PLATFORM_EXE), str(NUM_GAMES)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(PLATFORM_EXE.parent),
    )

    ready_event = threading.Event()
    stop_event = threading.Event()
    platform_lines = []
    monitor_thread = threading.Thread(
        target=monitor_platform_output,
        args=(platform_proc, ready_event, stop_event, platform_lines),
        daemon=True,
    )
    monitor_thread.start()

    print(f"[STEP 3/5] 等待 'Ready for connect.' (最长 {PLATFORM_READY_TIMEOUT}s)...")
    if not ready_event.wait(timeout=PLATFORM_READY_TIMEOUT):
        print("[FATAL] 平台未在超时内输出 Ready for connect.")
        stop_event.set()
        platform_proc.terminate()
        return 3

    print("[OK] 平台就绪。")
    time.sleep(1)

    print(f"[STEP 4/5] 启动 {len(CLIENTS)} 个客户端...")
    client_procs = []
    for name, path in CLIENTS:
        p = launch_client(name, path)
        if p is None:
            print(f"[FATAL] 客户端 {name} 启动失败")
            stop_event.set()
            platform_proc.terminate()
            return 4
        client_procs.append((name, p))
        time.sleep(PER_CLIENT_LAUNCH_GAP)

    print(f"[STEP 5/5] 等待平台跑完 {NUM_GAMES} 局 (最长 {GAME_RUN_TIMEOUT}s)...")
    try:
        platform_proc.wait(timeout=GAME_RUN_TIMEOUT)
        print(f"[OK] 平台正常退出，code={platform_proc.returncode}")
    except subprocess.TimeoutExpired:
        print("[WARN] 平台超时未退出，将强制终止以保证脚本结束")
        platform_proc.terminate()
        try:
            platform_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            platform_proc.kill()

    stop_event.set()

    print("[CLEANUP] 终止所有客户端进程...")
    for name, p in client_procs:
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    kill_residual_processes()

    # 解析日志：从 logs/yf1_m1_*.log 找 P0 改进标记
    print("\n=== 日志验证 ===")
    logs_dir = PROJECT_DIR / "logs"
    candidates = sorted(logs_dir.glob("yf1_m1_*.log"))
    if not candidates:
        print("[FAIL] 未找到 yf1_m1_*.log")
        return 5
    latest = candidates[-1]
    print(f"日志文件: {latest.name}")
    content = latest.read_text(encoding="utf-8", errors="replace")

    markers = ["【P0改进①】", "【P0改进②】", "【P0改进③】", "【P0改进④】", "【决策入口】"]
    summary = {}
    for m in markers:
        cnt = content.count(m)
        summary[m] = cnt
        print(f"  {m}: {cnt} 次")

    # 平台输出前 N 行，方便诊断
    print("\n=== 平台输出前 50 行 ===")
    for ln in platform_lines[:50]:
        print(f"  {ln}")

    if any(summary[m] > 0 for m in ["【P0改进①】", "【P0改进②】", "【P0改进③】", "【P0改进④】"]):
        print("\n[PASS] 至少一个 P0 改进被触发执行。")
        return 0
    elif summary["【决策入口】"] > 0:
        print("\n[PARTIAL] 决策入口被执行，但 P0 改进未触发（可能是这局未进入对应分支）。")
        return 0
    else:
        print("\n[FAIL] 决策入口未被触发——客户端未收到 act/play 请求。")
        # 最后 30 行日志方便排查
        tail = content.splitlines()[-30:]
        print("  日志最后 30 行:")
        for ln in tail:
            print(f"    {ln}")
        return 6


if __name__ == "__main__":
    sys.exit(main())
