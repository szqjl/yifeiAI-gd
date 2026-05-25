# Review: M1_vs_lalala.md — Accuracy Verification

## §2 — Passive() threshold (numofmy ≤ 10)

**Claim**: lalala's `passive()` calls `one_hand()` when `numofmy <= 10`.

**Source**: `lalala决策机制完整分析-02-passive.md:71` — `if numofmy <= 10:` (direct code quote).

**Verdict**: ✅ **CORRECT**. Threshold is exactly ≤10.

---

## §3 — Active() priority order

**Claim**: Priority order is:
1. 一手出完 → 2. 两手出完 → 3. 小单张 → 4. 三连对/钢板 → 5. 顺子 → 6. 三带二 → 7. 三张 → 8. 对子 → 9. 单张兜底

**Source**: `lalala决策机制完整分析-03-active.md:62-181` confirms this sequence.

**Verdict**: ✅ **Order is correct**.

**However**, the **straight threshold value is wrong**:

- M1 doc §3 (line 47): `顺子（顺子最小值 < cur[4]=8）`
- Actual source `cur = [9,10,9,8,10,10,2]` → `cur[4] = 10`, not 8.
- `lalala决策机制完整分析-03-active.md:40` quotes the same array, and line 216 correctly states `cur[4] = 10: 顺子阈值`.
- The error originates from a typo in 03-active.md:119 (`< 8（cur[4]）`) which M1_vs_lalala inherited.

**🔴 ERROR: Straight threshold should be `cur[4]=10`, not `cur[4]=8`.**

---

## §4 — Single() endgame condition

**Claim** (M1 doc §4, line 83): `if numofnext <= 4 or (numofpre <= 3 and numofpre >= 1):`

**Source**: `lalala决策机制完整分析-04-Single.md:98` — exact match: `if numofnext <= 4 or (numofpre <= 3 and numofpre >= 1):`

**Verdict**: ✅ **CORRECT**. Condition matches verbatim.

---

## §5 — Teammate protection logic

**Row-by-row verification against `lalala决策机制完整分析-04-Single.md`:**

| Row | M1 doc claim | Source | Verdict |
|-----|-------------|--------|---------|
| 队友出大牌，我有大牌 → 直接 PASS | 04-Single.md:100-103 (endgame: teammate greaterPos & curVal≥max_val → PASS; curVal≥15 & numofnext≠1 → PASS) | ✅ CORRECT |
| 队友剩牌 ≤ 4 → 只出大1的牌（精确控制） | 04-Single.md:144-153 (teammate greaterPos & numoffri≤4: `card_val[...] == curVal+1`) | ✅ CORRECT |
| 队友出大牌但我也有大牌 → 无特殊处理 | This row is **contradictory** to row 1 and inaccurate. lalala *does* have handling: in non-endgame, when teammate is greaterPos, `curVal >= 14 or curVal >= max_val-2 → PASS` (04-Single.md:140-141). This IS special handling. | ⚠️ **MISLEADING** — lalala handles this case; stating "无特殊处理" is incorrect. |
| 对手快冲关，队友领先 → 无 | 04-Single.md shows no such rule in lalala. | ✅ CORRECT (absent in lalala) |

---

## Additional errors / omissions found

### 🔴 1. Straight threshold (already noted in §3)
§3 line 47: `cur[4]=8` should be `cur[4]=10`.

### ⚠️ 2. §5 row 3 inaccuracy (already noted above)
"队友出大牌但我也有大牌 → 无特殊处理" is inconsistent with lalala source. lalala's `Single()` does have handling: if teammate is greaterPos (non-endgame), it PASSes when `curVal >= 14` or `curVal >= max_val-2` (04-Single.md:140-141). The table makes it seem like M1 over-protects while lalala has nothing, but in reality both have handling — just different mechanisms.

### ⚠️ 3. §4 bomb condition simplified
M1 doc §4 (line 122) states `pass_num >= 7` or `my_pass_num >= 5` → bomb, but the actual condition is more nuanced (04-Single.md:187-188):
```python
elif ((curVal >= 15 or curVal >= max_val-2) and numofgreaterPos <= 15) or pass_num >= 7 or my_pass_num >= 5:
```
The bomb condition has an **alternative path** (big card + few opponent cards) in addition to pass-count thresholds. This is a minor omission, not a factual error.

### ⚠️ 4. §9.1 "完全缺失的规则" — special() details omitted
The table mentions `pass_num>=5 → special()` but does not describe what `special()` does (04-Single.md:211-218: from-big-to-small, avoids bomb members, rank cards, and straight members). This context would strengthen the comparison.

### ✅ 5. No errors found in
- §1 positioning table
- §2 one_hand() description
- §4b active "一手出完" analysis
- §6 architecture comparison
- §7 performance statistics
- §8 core gap summary
- §9 missing/incomplete rules

---

## Summary of required corrections

| Location | Issue | Fix |
|----------|-------|-----|
| §3 line 47 | `cur[4]=8` → should be `cur[4]=10` | Change "顺子最小值 < cur[4]=8" to "顺子最小值 < cur[4]=10" |
| §5 table row 3 | "lalala: 无特殊处理" is misleading | Reword to describe actual lalala behavior (PASS on curVal≥14/≥max_val-2) or remove the row's implication that lalala has no handling |

---

## Self-evaluation: 🔥🔥🔥🔥 (very serious)
