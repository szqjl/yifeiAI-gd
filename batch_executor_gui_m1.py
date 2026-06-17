"""Phase 5 stub → scripts/gui/batch_executor_gui_m1.py"""
import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "scripts/gui/batch_executor_gui_m1.py"),
    run_name="__main__",
)
