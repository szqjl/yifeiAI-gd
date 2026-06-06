"""Generate replay_word.md excerpt for one game record."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NAMES = {0: "yf1_m3", 1: "对手@1", 2: "yf2_m3", 3: "对手@3"}


def main():
    fname = sys.argv[1] if len(sys.argv) > 1 else (
        "20260530220821279408 [yf1_m3]-[opponent_1_3]-[34]-[6].json"
    )
    p = REPO / "game_records" / fname
    d = json.loads(p.read_text(encoding="utf-8"))
    vn = (d.get("result") or {}).get("victoryNum") or d.get("victoryNum") or []
    hand0 = d.get("all_players_hands", {}).get("0", [])
    game_id = d.get("game_id", "")
    game_round = d.get("game_round", "?")
    level = "6"
    if "-[" in fname and fname.endswith("].json"):
        level = fname.rsplit("-[", 1)[-1].replace("].json", "")

    abs_path = p.resolve()
    rel_path = f"game_records/{fname}"
    replay_py = (REPO / "scripts" / "tools" / "yf_replay.py").resolve()

    blocks = [(20, 26), (36, 43), (52, 59)]
    excerpts = []
    for start, end in blocks:
        for i in range(start, min(end, len(d["actions"]))):
            a = d["actions"][i]
            pos = a["cur_pos"]
            ca = a["cur_action"]
            excerpts.append(
                f"--- 第 {i + 1} 步 ---\n"
                f"玩家{pos} ({NAMES.get(pos, pos)}) | {ca}\n"
            )

    content = f"""游戏记录：{fname}
game_id：{game_id}
round：{game_round}（文件名 `[{game_round}]`）
level：{level}
级数：批跑 GUA-029 后（`curRank={level}` 决策时）
victoryNum：{vn}

**GUA-029 典型点**：
- 第 23 步 yf1 **Bomb 3** 压对手三带二 9（R3 冲刺阻断）
- 第 41 步 yf2 **Bomb** 回炸对手 J 炸弹（R2 回炸）
- 第 55 步 yf1 **Bomb T** 回炸对手 2 炸弹（R2 回炸）

回放命令（PowerShell，复制下面整行执行，不要只复制路径）：

```powershell
python "{replay_py}" "{abs_path}"
```

或已在仓库根目录时：

```powershell
.\\YF_REPLAY.bat "{rel_path}"
```

注意：`game_id` 与 `[yf1_m3]` 之间**必须有空格**。

【发牌后初始手牌】
玩家0 (yf1_m3) | {hand0}
玩家1 (对手@1) | []
玩家2 (yf2_m3) | []
玩家3 (对手@3) | []

【出牌步骤 · 摘录 GUA-029 炸弹焦点】
{''.join(excerpts)}"""
    out = REPO / "replay_word.md"
    out.write_text(content, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
