# GUA-087 · v7 · actions 流水漏 tribute 阶段出牌

> **状态**：observation 📝 (草稿 2026-06-29) — 非阻塞，文档说明即可  
> **严重级别**：P2（语义不完整，**不影响牌谱回放主路径**）  
> **标签**：v7, recorder, actions, observation  
> **发现路径**：批量统计 game_records_v7/*.json initial_hand 长度分布（30 副，2026-06-29）

---

## 1. 现象

ctions[] 流水只含**出牌阶段** notify；**进/还贡阶段 yf1 自己的出牌没进流水**。

证据：30 副牌谱全 28 张起手（起手 27 + 还贡 1）= 出牌阶段 27 张（已出 + 残牌） → **差 1 张**。

- 出+残（统计 ctions[].cur_pos=0.cur_action[2]）= 27
- 起手（initial_hand 28）= 27 + 1(还贡收)
- 实际送进贡的 1 张 = **不在 ctions 流水里**

---

## 2. 根因（实锤）

7_game_recorder.py 中：

- 
ecord_play_notify（ct 阶段，cur_pos=0 出牌）→ 写 ctions[]
- 
ecord_tribute_notify / 
ecord_back_notify（**收方** notify）→ 写 my_decisions[] + djust_initial_hand_for_tribute_back(add)
- **_handle_tribute_action / _handle_back_action（送方 ct 阶段）** → yf1_v7.py:373, 397 仅 
ecord_decision（写 my_decisions[]），**不写 ctions[]**

→ 平台协议上 	ribute/ack 阶段 ct 消息**没有对应 
otify**（出完就完，不会再收到自己"出 XX"的 notify），所以 
ecord_play_notify 不会被触发。

---

## 3. 影响（已查清：非阻塞）

- ctions[] 流水**少 1 张**（tribute 出牌）
- ctions[] 长度 ≠ yf1 实际出牌数
- **但**：my_decisions[] 完整记录所有决策（出牌 + tribute + back）
- **回放主路径**（scripts/tools/yf_replay.py）**已独立处理进还贡**：
  - pply_tribute_back_to_hand（L70）按 my_decisions 重算 initial_hand
  - 不依赖 ctions[] 完整性
- **结论**：**不影响回放、不影响 KPI 计算、不影响 ML 训练**（ML 读 my_decisions）

### 唯一已知用途：按 ctions[] 重算手数的诊断脚本

scripts/analysis/initial_hand_audit.py 等可能用 ctions 流水对账——若此类脚本存在，需额外加 +1(tribute 出) 的修正（**可参考 GUA-087 衍生脚本**）。


## 4. 决策：documentation-only（方案 C 实施）

yf_replay.py 已用 my_decisions 独立处理进还贡，ctions[] 完整性**不阻塞**任何下游。
**不动代码**，仅在 docs/guandan-brain/knowledge/platform-data-interpretation.md（或牌谱-schema 文档）加一行说明：

> ctions[] 仅含出牌阶段 notify；进/还贡阶段 yf1 自己的出牌**不在 actions 流水**，但**完整记录于 my_decisions[] 的 	ribute/ack 项**。yf_replay.py:70 pply_tribute_back_to_hand 据此还原出牌前手牌。


## 5. 完成定义（documentation-only）

- [ ] 在 docs/guandan-brain/knowledge/platform-data-interpretation.md 添加本条说明
- [ ] 标注 ctions[] 字段 schema 含义边界
- [ ] 若有 scripts/analysis/* 用 ctions 重算手数的脚本，附上 +1(tribute 出) 修正说明


## 6. 关联

- **GUA-086**（草稿）：tribute remove 传参错（本流水缺失与 GUA-086 一起源自同一调用点）
- **GUA-067**：tribute 调整 initial_hand
- **数据来源**：game_records_v7/*.json 30 副 28 张的 100% 含 	ribute/ack 决策条目
