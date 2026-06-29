# GUA-086 · v7 · 进/还贡出牌 remove 路径传参错

> **状态**：**closed ✅** (修复 + 验证 2026-06-29)  
> **严重级别**：原 P1 → **closed**（修复后 v1006 协议下语义完全正确）  
> **标签**：v7, recorder, tribute, GUA-067-followup  
> **修复模块**：src/communication/yf1_v7.py:373, 397（同款 yf2_v7.py:373, 397）

---

## 1. 现象

日志 logs/yf1_v7_20260629_083432.log：

`
[08:35:02] [GameRecorder.yf1_v7] [WARNING] ⚠ 贡牌调整: TRIBUTETRIBUTE 不在 initial_hand 中，无法移除 (共27张)
[08:35:02] [GameRecorder.yf1_v7] [INFO] ✓ 贡牌调整: S3 加入 initial_hand (共28张)
... (10 次 remove 失败 + 10 次 add 成功)
`

- **
emove 永远失败**（卡牌字面 "TRIBUTETRIBUTE" 不在 initial_hand）
- **dd 正常**（收方 notify 路径传单张 card_str）

---

## 2. 根因（实锤）

src/communication/yf1_v7.py:370：

`python
selected = action_list[act_index]   # selected = ["tribute","tribute",["SB"]]（平台 actionList 项）
selected = action_list[act_index]   # 整个三元组
self.game_recorder.adjust_initial_hand_for_tribute_back(selected, "remove")
#                                                                          ^^^^^^^^^ 错！应传 selected[2][0]
`

→ 传入 7_game_recorder.adjust_initial_hand_for_tribute_back 的 card_raw 是 ["tribute","tribute",["SB"]] 整个 list。

_normalize_tribute_back_card 实现（7_game_recorder.py:790）：

`python
def _normalize_tribute_back_card(card: Any) -> Optional[str]:
    normalized = normalize_cards_to_string_list([card])  # 入口规范
    if not normalized: return None
    raw = normalized[0]
    if isinstance(raw, str) and len(raw) >= 2:
        return raw[0].upper() + raw[1:].upper()
    return raw
`


ormalize_cards_to_string_list([card]) 对 card = ["tribute","tribute",["SB"]]：

- isinstance(card, str) = False
- isinstance(card, list) and len(card) >= 2 = True
- 
esult.append(f"{str(card[0])}{str(card[1])}") = "tributetribute"
- 大写化 = **"TRIBUTETRIBUTE"**

→ 与 initial_hand 中任何单张（如 "SB"）均不匹配 → warn + 不移除。

---

## 3. 影响范围

- 同一 bug 在 yf1_v7.py **L373（tribute 出）** 和 **L397（back 出）** 都有
- yf2_v7.py **L373, L397** 同款
- **共 4 处**需要修
- **不致命**：
ecord_game_start 写入的 initial_hand 是 v1006 起手 27 张；	ribute 阶段 remove 即使失败也不影响语义（27 张里本来就没 yf1 送出的那张——gameStart 时手牌尚未送出）
- **但**：与 
ecord_back_notify 的 dd 路径配合时，最终 initial_hand = 27 + 1(还贡收) = 28，**整体语义仍正确**，仅**单步 remove 失败**是冗余无效操作

---

## 4. 修复

### 方案 A（推荐）：传 selected[2][0]

`python
# yf1_v7.py L370-373
selected = action_list[act_index]
selected_card = selected[2][0] if len(selected) >= 3 and selected[2] else None
print(f"[进贡] 轮到自己进贡，选择: {selected}")
self.game_recorder.adjust_initial_hand_for_tribute_back(selected_card, "remove")
`

### 方案 B：防御性 normalize

在 djust_initial_hand_for_tribute_back 内增加：若 card_raw 是 list/tuple 且含 [2][0]，则取 card_raw[2][0]。**对调用方零侵入**，但会掩盖其他 call site 的同类错误。

### 方案 C：抽 xtract_tribute_card(action) helper

7_game_recorder 暴露一个规范化函数，调用方统一从 selected 提取单张。

---

## 5. 完成定义（草稿）

- [ ] yf1_v7.py / yf2_v7.py L373, L397 改用 selected[2][0]（或 helper）
- [ ] pytest 覆盖 4 处
- [ ] 日志不再出现 TRIBUTETRIBUTE / BACKBACK 警告
- [ ] 净盘后跑 1 局（≥ 1 副有贡还），断言：
  - initial_hand 最终长度 = 28（起手 27 + 还贡 1）
  - len(actions[].cur_pos=0.cur_action[2]) + len(my_decisions[tribute].action[2]) = 28
  - len(actions[].cur_pos=0.cur_action[2]) + restCards[0] = 27（差 1 张是 tribute 出，未进 actions 流水）— **见 GUA-087**

---

## 6. 关联

- **GUA-067**：tribute 调整 initial_hand 的初版
- **GUA-087**（草稿）：actions 流水漏 tribute 阶段出牌
- **7_game_recorder.adjust_initial_hand_for_tribute_back**：函数实现 OK（L831-848），问题在调用方传错形态


---

## 7. 完成（2026-06-29）

### 修复实施

| 文件 | 改动 |
|------|------|
| src/communication/yf1_v7.py | +1 helper _extract_tribute_back_card + 2 调用点改用 |
| src/communication/yf2_v7.py | 同款 |
| 	ests/test_gua086_tribute_remove_wrong_arg.py | 新增 13 用例（**13/13 PASS**） |

### 净盘批跑验证（2026-06-29 12:00，3 局 36 副）

| 指标 | 修前（旧 log） | 修后（本次） |
|------|---------------|-------------|
| TRIBUTETRIBUTE / BACKBACK 警告 | **10** | **0** ✅ |
| 不在 initial_hand 中，无法移除 警告 | **10** | **0** ✅ |
| dd 路径成功 | 10 | **17** ✅ |
| 
emove 路径成功（修前永远失败） | 0 | **17** ✅ |
| **add/remove 配对** | 10 vs 0（不对称） | **17 vs 17（完美对称）** |

**
emove 路径从"0 成功"变成"17 成功"——GUA-086 修复实质性生效。**

### vn 对账

- latest_victory_num.json: n=[0,3,0,3], n_source=gameResult（平台直采，**未走 fallback**）
- 7_vs_lalala_scores.json: 	eam_a=0, team_b=3, total=3（0+3=3 ✅）
- 队内一致：[0]=[2]=True [1]=[3]=True ✅
- V7 队 0/3 局（lalala 仍占优；本批 K 牌力差距未解，但**GUA-086 修复本身已闭环**）

### pytest 留存

- 	ests/test_gua086_tribute_remove_wrong_arg.py 13/13 PASS，下次回归可直接跑：
  `ash
  python -m pytest tests/test_gua086_tribute_remove_wrong_arg.py -v
  `

### 完成定义（已达成）

- [x] yf1_v7.py / yf2_v7.py L373, L397 改用 selected[2][0] helper（_extract_tribute_back_card）
- [x] pytest 覆盖 4 处调用 + 端到端集成（13/13 PASS）
- [x] 净盘后跑 3 局 36 副，日志无 TRIBUTETRIBUTE 警告
- [x] vn 对账：platform 直采，server_vn_raw == victoryNum，队内一致
- [x] add/remove 配对：17 vs 17

---

## 8. 遗留与后续（**非阻塞**）

### GUA-087 降级保留 P3

- ctions[] 流水**仍缺 tribute 阶段 yf1 自己出的 1 张**（仅 my_decisions 完整）
- **不影响**：yf_replay.py:70 apply_tribute_back_to_hand 已独立处理进还贡
- **本次净盘 36 副全 27 张 + delta=0**，未触发 28 张副路径（lalala 全第一）
- **后续**：documentation-only 补 platform-data-interpretation.md 说明，详见 [[v7-gua087-actions-stream-missing-tribute]]

### 牌力差距

- V7 队 0/3 局全负给 lalala——属 GUA-072/075/080 等 P0 范畴，与本修复无关
