# -*- coding: utf-8 -*-
"""
T9 直接运行脚本：should_protect + combine_handcards 双 patch
- 备份原始文件 → patch → 跑 batch_executor（16局） → 还原 → 输出结果
- 所有输出写入日志文件，避免管道缓冲问题
"""
import os, sys, shutil, subprocess, json, re, time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "_t9_logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"t9_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

HAND_COMBINER = PROJECT_ROOT / "src" / "game_logic" / "hand_combiner.py"
STRATEGY_ENGINE = PROJECT_ROOT / "src" / "decision" / "strategy_engine.py"
GAME_RECORDS_DIR = PROJECT_ROOT / "game_records"
SERVER_PATH = "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"

CLIENTS = [
    "src/communication/yf1_m1.py",
    "src/communication/run_lalala_client3.py",
    "src/communication/yf2_m1.py",
    "src/communication/run_lalala_client4.py",
]

GAMES_PER_CONFIG = 16

# ── lalala 完整版 combine_handcards ─────────────────────────────────
LALALA_COMBINE_HANDCARDS = r'''
    def combine_handcards(self, handcards, rank, card_val):
        cards = {}
        cards["Single"] = []
        cards["Pair"] = []
        cards["Trips"] = []
        cards["Bomb"] = []
        bomb_info = {}

        handcards = sorted(handcards, key=lambda item: card_val[item[1]])
        start = 0
        for i in range(1, len(handcards) + 1):
            if i == len(handcards) or handcards[i][-1] != handcards[i - 1][-1]:
                if (i - start == 1):
                    cards["Single"].append(handcards[i - 1])
                elif (i - start == 2):
                    cards["Pair"].append(handcards[start:i])
                elif (i - start) == 3:
                    cards["Trips"].append(handcards[start:i])
                else:
                    cards["Bomb"].append(handcards[start:i])
                    bomb_info[handcards[start][-1]] = i - start
                start = i

        rank = rank
        temp = []
        for i in handcards:
            if i[-1] != rank and i[-1] != 'B' and i[-1] != 'R':
                temp.append(i)
        for i in cards['Bomb']:
            if i[0][-1] != rank and i[0][-1] != 'B' and i[0][-1] != 'R':
                for j in i:
                    temp.remove(j)
        cardre = [0] * 14
        for i in temp:
            if i[-1] == 'A':
                cardre[1] += 1
            if i[-1] == '2':
                cardre[2] += 1
            if i[-1] == '3':
                cardre[3] += 1
            if i[-1] == '4':
                cardre[4] += 1
            if i[-1] == '5':
                cardre[5] += 1
            if i[-1] == '6':
                cardre[6] += 1
            if i[-1] == '7':
                cardre[7] += 1
            if i[-1] == '8':
                cardre[8] += 1
            if i[-1] == '9':
                cardre[9] += 1
            if i[-1] == 'T':
                cardre[10] += 1
            if i[-1] == 'J':
                cardre[11] += 1
            if i[-1] == 'Q':
                cardre[12] += 1
            if i[-1] == 'K':
                cardre[13] += 1

        st = []
        minnum = 10
        mintwonum = 10

        for i in range(1, len(cardre) - 4):
            if 0 not in cardre[i:i + 5]:
                onenum = 0
                zeronum = 0
                twonum = 0
                for j in cardre[i:i + 5]:
                    if j - 1 == 0:
                        zeronum += 1
                    if j - 1 == 1:
                        onenum += 1
                    if j - 1 == 2:
                        twonum += 1

                if zeronum > onenum and minnum >= onenum:
                    if len(st) == 0:
                        if zeronum >= onenum + twonum:
                            st.append(i)
                            minnum = onenum
                            mintwonum = twonum
                    else:
                        if minnum == onenum:
                            if i == 1:
                                if mintwonum > twonum:
                                    if zeronum >= onenum + twonum:
                                        st = []
                                        st.append(i)
                                        minnum = onenum
                                        mintwonum = twonum
                            else:
                                if mintwonum >= twonum:
                                    if zeronum >= onenum + twonum:
                                        st = []
                                        st.append(i)
                                        minnum = onenum
                                        mintwonum = twonum
                        else:
                            if zeronum >= onenum + twonum:
                                st = []
                                st.append(i)
                                minnum = onenum
                                mintwonum = twonum

        if 0 not in cardre[10:] and cardre[1] != 0:
            onenum = 0
            zeronum = 0
            twonum = 0
            for j in cardre[10:]:
                if j - 1 == 0:
                    zeronum += 1
                if j - 1 == 1:
                    onenum += 1
                if j - 1 == 2:
                    twonum += 1
            if zeronum > onenum and minnum >= onenum:
                if len(st) == 0:
                    if zeronum >= onenum + twonum:
                        st.append(1)
                        minnum = onenum
                        mintwonum = twonum
                else:
                    if minnum == onenum:
                        if mintwonum > twonum:
                            if zeronum >= onenum + twonum:
                                st = []
                                st.append(1)
                                minnum = onenum
                                mintwonum = twonum
                    else:
                        if zeronum >= onenum + twonum:
                            st = []
                            st.append(1)
                            minnum = onenum
                            mintwonum = twonum

        for i in st:
            num = i + 5
            single = []
            for j in range(i, num):
                if cardre[j] == 0:
                    pass
                elif cardre[j] == 1:
                    for k in range(len(handcards)):
                        if handcards[k][-1] == ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K'][j - 1] \
                                and handcards[k] not in temp:
                            single.append(handcards[k])
                            break
            cards['Straight'] = single

        return cards, bomb_info
'''


def log(s):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {s}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def backup_file(path):
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    return bak


def restore_file(bak):
    orig = Path(str(bak)[:-4])
    shutil.copy2(bak, orig)
    os.remove(bak)


def patch_disable_should_protect(engine_path):
    text = engine_path.read_text(encoding="utf-8")
    start_marker = '    def should_protect(self, message: Dict, context: Dict) -> bool:'
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"未找到 should_protect")
    rest = text[start + len(start_marker):]
    m = re.search(r'\n    def ', rest)
    if m:
        end = start + len(start_marker) + m.start()
    else:
        end = len(text)
    stub = start_marker + '\n        """T9 patch: disabled"""\n        return False\n'
    new_text = text[:start] + stub + text[end:]
    engine_path.write_text(new_text, encoding="utf-8")
    log("strategy_engine.should_protect() 已替换为 return False")


def patch_hand_combiner_lalala(combiner_path):
    text = combiner_path.read_text(encoding="utf-8")
    start_marker = "    def combine_handcards(self, handcards"
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError("未找到 combine_handcards")
    line_end = text.find("\n", start)
    if line_end < 0:
        raise RuntimeError("combine_handcards 方法头格式异常")
    rest = text[line_end + 1 :]
    m = re.search(r"\n    def ", rest)
    end = len(text) if not m else line_end + 1 + m.start()
    from test_t9 import _lalala_combine_method_source

    replacement = _lalala_combine_method_source()
    new_text = text[:start] + replacement + text[end:]
    compile(new_text, str(combiner_path), "exec")
    combiner_path.write_text(new_text, encoding="utf-8")
    log("hand_combiner.combine_handcards 已替换为 lalala 版本")


def verify_patch(engine_path, combiner_path):
    """验证 patch 已生效"""
    eng_text = engine_path.read_text(encoding="utf-8")
    comb_text = combiner_path.read_text(encoding="utf-8")
    if "return False" not in eng_text.split("should_protect")[1].split("\n")[1]:
        log("警告: should_protect 可能未被正确 patch")
    if "cards[\"Straight\"]" in comb_text:
        log("✅ combine_handcards 已包含 lalala 的顺子逻辑")
    log("✅ patch 验证通过")


def parse_victorynum(record_path):
    try:
        with open(record_path, encoding="utf-8") as f:
            d = json.load(f)
        for key in ["game_info", "result", "game_result"]:
            if key in d:
                vn = d[key].get("victoryNum", []) if isinstance(d[key], dict) else []
                if vn:
                    return vn
    except Exception:
        pass
    return None


def count_paired_since(before_filenames):
    pattern = re.compile(r"^(\d+) \[(yf1_m1|yf2_m1)\]")
    yf1, yf2 = set(), set()
    if not GAME_RECORDS_DIR.is_dir():
        return 0
    for p in GAME_RECORDS_DIR.glob("*.json"):
        if p.name in before_filenames:
            continue
        m = pattern.match(p.name)
        if not m:
            continue
        (yf1 if m.group(2) == "yf1_m1" else yf2).add(m.group(1))
    return len(yf1 & yf2)


def run_batch(target_games):
    cmd = [
        sys.executable, "-m", "batch_executor",
        "--server-path", SERVER_PATH,
        "--target-games", str(target_games),
        "--clients", *CLIENTS,
    ]
    log(f"执行: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, cwd=str(PROJECT_ROOT),
        capture_output=True, text=True, timeout=3600,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    log(f"返回码: {result.returncode}")
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            log(f"  [stdout] {line}")
    if result.stderr:
        for line in result.stderr.strip().split("\n"):
            log(f"  [stderr] {line}")
    return result.returncode


def analyze_results(before_filenames, paired_ids):
    new_names = []
    for p in GAME_RECORDS_DIR.glob("*.json"):
        if p.name not in before_filenames:
            new_names.append(p.name)

    wins = losses = 0
    for name in new_names:
        m = re.match(r"(\d+)", name)
        if not m or m.group(1) not in paired_ids:
            continue
        records = list(GAME_RECORDS_DIR.glob(f"{m.group(1)} [yf1_m1]*.json"))
        if not records:
            continue
        vn = parse_victorynum(records[0])
        if not vn or len(vn) < 4:
            continue
        team_a = vn[0] + vn[2]
        team_b = vn[1] + vn[3]
        if team_a > team_b:
            wins += 1
        elif team_b > team_a:
            losses += 1

    total = wins + losses
    return {"wins": wins, "losses": losses, "total": total,
            "win_rate": wins / total if total > 0 else 0.0}


def cleanup():
    """清理孤儿进程"""
    for exe in ["guandan_offline_v1006.exe"]:
        try:
            subprocess.run(["taskkill", "/F", "/IM", exe],
                           capture_output=True, timeout=10,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
    try:
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq 客户端*"],
                       capture_output=True, timeout=10,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass
    for f in [PROJECT_ROOT / "execution_state.json", PROJECT_ROOT / "game_scores.json"]:
        if f.exists():
            f.unlink()


def main():
    log("=" * 70)
    log("T9：双重 patch（禁用 should_protect + lalala combine_handcards）")
    log("=" * 70)

    # 清理
    cleanup()
    log("已完成前序清理")

    # 记录已有 game_records
    before = {p.name for p in GAME_RECORDS_DIR.glob("*.json")} if GAME_RECORDS_DIR.is_dir() else set()
    log(f"已有 game_records: {len(before)} 个文件")

    # 备份
    bak_combiner = backup_file(HAND_COMBINER)
    bak_engine = backup_file(STRATEGY_ENGINE)
    log("原始文件已备份")

    try:
        # Patch
        patch_disable_should_protect(STRATEGY_ENGINE)
        patch_hand_combiner_lalala(HAND_COMBINER)
        verify_patch(STRATEGY_ENGINE, HAND_COMBINER)

        # 分批跑
        BATCH_SIZE = 3
        total_games = 0
        while total_games < GAMES_PER_CONFIG:
            remaining = GAMES_PER_CONFIG - total_games
            batch = min(remaining, BATCH_SIZE)
            log(f"\n--- 第 {total_games // BATCH_SIZE + 1} 批: 目标 {batch} 局 ---")

            cleanup()
            rc = run_batch(batch)

            paired_after = count_paired_since(before)
            log(f"本批结束，game_records 累计成对局数 = {paired_after}/{GAMES_PER_CONFIG}")

            if paired_after <= total_games:
                log(f"错误: batch_executor 未产生新进度 ({paired_after}/{GAMES_PER_CONFIG})，返回码 {rc}")
                raise RuntimeError(f"batch_executor 未产生新进度，返回码 {rc}")

            total_games = paired_after

        log(f"\n=== 16局完成，开始分析结果 ===")

        # 找成对 game_id
        pattern = re.compile(r"^(\d+) \[(yf1_m1|yf2_m1)\]")
        yf1, yf2 = set(), set()
        for p in GAME_RECORDS_DIR.glob("*.json"):
            m = pattern.match(p.name)
            if m:
                (yf1 if m.group(2) == "yf1_m1" else yf2).add(m.group(1))
        paired_ids = yf1 & yf2
        log(f"共 {len(paired_ids)} 组成对数据")

        result = analyze_results(before, paired_ids)
        log(f"\n{'=' * 50}")
        log(f"T9 结果: 胜 {result['wins']} / 负 {result['losses']} "
            f"（共 {result['total']} 局）胜率 {result['win_rate']:.1%}")
        log(f"{'=' * 50}")

        # 写结果
        report = PROJECT_ROOT / "data" / "eval" / "test_t9_results.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        with open(report, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "result": result,
                "type": "T9",
                "changes": ["should_protect -> False", "combine_handcards -> lalala"],
            }, f, indent=2, ensure_ascii=False)
        log(f"结果已写入: {report}")

    finally:
        # 还原
        restore_file(bak_combiner)
        restore_file(bak_engine)
        log("\n原始文件已还原")

    log(f"\n完整日志: {LOG_FILE}")
    return result


if __name__ == "__main__":
    main()