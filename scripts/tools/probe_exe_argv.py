# -*- coding: utf-8 -*-
"""Probe guandan_offline_v1006.exe argv handling (boot stdout only)."""
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXE = REPO / "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"


def kill_server():
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/IM", "guandan_offline_v1006.exe"],
            capture_output=True,
            text=True,
        )


def probe(argv_list):
    kill_server()
    time.sleep(1)
    cmd = [str(EXE)] + argv_list
    print("=== argv:", cmd, "===")
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(EXE.parent),
    )
    lines = []
    t0 = time.time()
    while time.time() - t0 < 10:
        line = p.stdout.readline()
        if not line:
            if p.poll() is not None:
                break
            time.sleep(0.1)
            continue
        lines.append(line.rstrip())
        if "Ready for connect" in line:
            break
    try:
        p.terminate()
        p.wait(timeout=3)
    except Exception:
        p.kill()
    kill_server()
    for ln in lines:
        print(ln)
    print("--- lines:", len(lines), "---\n")
    return lines


def main():
    if not EXE.exists():
        print("missing", EXE)
        sys.exit(1)
    for n in ["1", "3", "10"]:
        probe([n])
    probe([])


if __name__ == "__main__":
    main()
