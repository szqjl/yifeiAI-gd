# -*- coding: utf-8 -*-
"""启动 lalala client3（座位 1）。"""

import sys
from pathlib import Path

# 确保从项目根目录启动时也能找到 _lalala_launcher
_comm_dir = str(Path(__file__).resolve().parent)
if _comm_dir not in sys.path:
    sys.path.insert(0, _comm_dir)

from _lalala_launcher import launch_lalala_client

if __name__ == "__main__":
    launch_lalala_client("client3")
