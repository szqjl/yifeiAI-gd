# -*- coding: utf-8 -*-
"""Q1 规则表静态校验脚本。"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_ROOT = os.path.join(REPO_ROOT, "src")
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, SRC_ROOT)

from src.v.nn.endgame.endgame_preprocessor import (  # noqa: E402
    format_q1_rule_table_validation_errors,
    validate_q1_rule_table_consistency,
)


def main() -> int:
    errors = validate_q1_rule_table_consistency()
    if errors:
        print("Q1 rule table validation FAILED")
        print(format_q1_rule_table_validation_errors(errors))
        return 1

    print("Q1 rule table validation PASS")
    print("checked: endgame_rule, BAOSHU_RULE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
