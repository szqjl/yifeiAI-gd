# -*- coding: utf-8 -*-
"""Phase 5 stub → scripts/gui/start_gui.py"""
import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "scripts/gui/start_gui.py"),
    run_name="__main__",
)
