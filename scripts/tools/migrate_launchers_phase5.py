#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 5：将根目录 .bat 迁入 scripts/launchers/ 并生成根目录薄 stub。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAUNCHERS = ROOT / "scripts" / "launchers"

# 根目录 bat -> launchers 子目录
MAPPING: dict[str, str] = {
    "START_M1_GUI.bat": "m",
    "START_M2_GUI.bat": "m",
    "START_M3_GUI.bat": "m",
    "START_M1_TRAINING.bat": "m",
    "START_M1_WORKFLOW_FULL.bat": "m",
    "START_AUTO_RESTART_WORKFLOW.bat": "workflow",
    "START_V4_GUI.bat": "v-learn",
    "START_V5_GUI.bat": "v-learn",
    "START_V6_GUI.bat": "v-learn",
    "START_V5_CLIENTS.bat": "v-learn",
    "START_V7_GUI.bat": "v-nn",
    "START_V7_COMPLETE.bat": "v-nn",
    "START_V7_AUTO.bat": "v-nn",
    "START_V7_CLIENTS.bat": "v-nn",
    "START_SMART_TRAINING.bat": "training",
    "START_STAGE7_TRAINING.bat": "training",
    "START_STRATEGY_TASKS_TRAINING.bat": "training",
    "QUICK_START_STAGE7.bat": "training",
    "QUICK_START_STAGE7_ULTRA.bat": "training",
    "INSTALL_STAGE7_DEPENDENCIES.bat": "training",
    "YF_REPLAY.bat": "tools",
    "CHECK_RECORD_CONSISTENCY.bat": "checks",
    "batch_convert_replays.bat": "tools",
    "run_stage6_training_gui.bat": "training",
    "run_new_test.bat": "tools",
}

STUB_TEMPLATE = """@echo off
REM Phase 5 stub → scripts/launchers/{subdir}/{name}
cd /d "%~dp0"
call "%~dp0scripts\\launchers\\{subdir}\\{name}" %*
"""

ENV_CALL = 'call "%~dp0..\\_env.bat"\r\n'


def transform_content(name: str, text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    env_inserted = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip().lower()
        if not env_inserted and (
            stripped.startswith("@echo off")
            or stripped.startswith("rem ")
            or stripped == "rem"
            or stripped.startswith("chcp ")
            or stripped.startswith("setlocal")
        ):
            out.append(line)
            if stripped.startswith("@echo off"):
                out.append(ENV_CALL)
                env_inserted = True
            i += 1
            continue
        if stripped in ("cd /d \"%~dp0\"", "cd /d %~dp0"):
            i += 1
            continue
        line = line.replace('cd /d %~dp0 &&', "cd /d %REPO_ROOT% &&")
        line = line.replace('cd /d "%~dp0" &&', 'cd /d "%REPO_ROOT%" &&')
        line = line.replace("call START_V7_CLIENTS.bat", 'call "%~dp0START_V7_CLIENTS.bat"')
        line = line.replace("py yf_replay.py", "python scripts/tools/yf_replay.py")
        line = line.replace(
            "D:\\guandanscore\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe 10",
            "%REPO_ROOT%\\offline_platform\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe 10",
        )
        line = line.replace("必须在 m1-dev 分支运行", "请在 m-dev 分支运行")
        if name == "START_M1_WORKFLOW_FULL.bat" and "set SERVER_PATH=" in line and "D:\\GDAI" in line:
            line = (
                'set "SERVER_PATH=%REPO_ROOT%\\offline_platform\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe"\r\n'
            )
        out.append(line)
        i += 1
    if not env_inserted:
        out.insert(0, "@echo off\r\n" + ENV_CALL)
    return "".join(out)


def main() -> None:
    for sub in set(MAPPING.values()):
        (LAUNCHERS / sub).mkdir(parents=True, exist_ok=True)

    for name, subdir in sorted(MAPPING.items()):
        src = ROOT / name
        if not src.is_file():
            print(f"SKIP missing {name}")
            continue
        body = transform_content(name, src.read_text(encoding="utf-8", errors="replace"))
        dst = LAUNCHERS / subdir / name
        dst.write_text(body, encoding="utf-8", newline="\r\n")
        stub = STUB_TEMPLATE.format(subdir=subdir, name=name)
        (ROOT / name).write_text(stub, encoding="utf-8", newline="\r\n")
        print(f"OK {name} -> launchers/{subdir}/")

    print("Done. pre_push_check.bat left at repo root (dev convention).")


if __name__ == "__main__":
    main()
