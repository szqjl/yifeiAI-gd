# -*- coding: utf-8 -*-
"""Minimal 4-client WS sniffer: verify exe argv -> settingTimes / victoryNum."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

try:
    from ws4py.client.threadedclient import WebSocketClient
except ImportError:
    print("pip install ws4py")
    sys.exit(1)

REPO = Path(__file__).resolve().parents[2]
EXE = REPO / "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"
CLIENTS_DIR = REPO / "offline_platform/guandan_offline_v1006/clients"


class Sniffer(WebSocketClient):
    def __init__(self, url, name, sink):
        super().__init__(url)
        self.name = name
        self.sink = sink
        self.action = None
        try:
            sys.path.insert(0, str(CLIENTS_DIR))
            from action import Action  # noqa: WPS433

            self.action = Action()
        except Exception:
            self.action = None

    def received_message(self, message):
        msg = json.loads(str(message))
        stage = msg.get("stage")
        if stage in ("gameOver", "gameResult"):
            self.sink.append(
                {
                    "client": self.name,
                    "stage": stage,
                    "curTimes": msg.get("curTimes"),
                    "settingTimes": msg.get("settingTimes"),
                    "victoryNum": msg.get("victoryNum"),
                    "final": msg.get("final"),
                }
            )
        if "actionList" in msg and self.action is not None:
            idx = self.action.parse(msg)
            self.send(json.dumps({"actIndex": idx}))


def kill_server():
    subprocess.run(
        ["taskkill", "/F", "/IM", "guandan_offline_v1006.exe"],
        capture_output=True,
        text=True,
    )


def probe(argv_n: int, timeout: int = 600) -> dict:
    kill_server()
    time.sleep(1)
    hits: list[dict] = []
    server_lines: list[str] = []

    proc = subprocess.Popen(
        [str(EXE), str(argv_n)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(EXE.parent),
    )

    def read_server():
        assert proc.stdout is not None
        for line in proc.stdout:
            server_lines.append(line.rstrip())

    threading.Thread(target=read_server, daemon=True).start()

    t0 = time.time()
    while time.time() - t0 < 30:
        if any("Ready for connect" in ln for ln in server_lines):
            break
        if proc.poll() is not None:
            break
        time.sleep(0.2)

    if not any("Ready for connect" in ln for ln in server_lines):
        kill_server()
        return {"argv_n": argv_n, "error": "not ready", "boot": server_lines}

    time.sleep(2)
    clients = []
    for i in range(1, 5):
        c = Sniffer(f"ws://127.0.0.1:23456/game/probe{i}", f"c{i}", hits)
        c.connect()
        clients.append(c)
        threading.Thread(target=c.run_forever, daemon=True).start()
        time.sleep(0.3)

    t0 = time.time()
    done = False
    while time.time() - t0 < timeout:
        if any(h.get("stage") == "gameResult" for h in hits):
            done = True
            break
        if any("达到设定游戏次数" in ln for ln in server_lines):
            done = True
            break
        if proc.poll() is not None:
            break
        time.sleep(0.5)

    for c in clients:
        try:
            c.close()
        except Exception:
            pass
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    kill_server()

    setting_lines = [ln for ln in server_lines if "设定的游戏次数" in ln or "0号位胜利" in ln]
    return {
        "argv_n": argv_n,
        "done": done,
        "ws_hits": hits,
        "server_setting_or_victory": setting_lines,
        "server_tail": server_lines[-20:],
    }


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true", help="run argv 1 then 3")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("-o", "--output", help="write JSON result to file")
    args = ap.parse_args()
    if args.compare:
        results = [probe(1), probe(3)]
        payload = results
    else:
        payload = probe(args.n)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
