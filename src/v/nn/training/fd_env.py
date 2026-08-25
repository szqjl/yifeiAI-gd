# -*- coding: utf-8 -*-
"""将 external/FableDan 加入 sys.path（fd_native DMC 自对弈）。"""

from __future__ import annotations

import sys
from pathlib import Path

_FABLE_ROOT: Path | None = None


def fabledan_root() -> Path:
    global _FABLE_ROOT
    if _FABLE_ROOT is None:
        _FABLE_ROOT = Path(__file__).resolve().parents[4] / "external" / "FableDan"
    return _FABLE_ROOT


def ensure_fabledan_importable() -> Path:
    root = fabledan_root()
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    return root
