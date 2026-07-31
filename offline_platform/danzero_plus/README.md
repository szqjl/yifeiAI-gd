# DanZero / DanZero+ 源码（第三方支撑工件）

> 来源：`https://github.com/Zhixinghgd/danzero_plus`（「本地化原danzero+代码」）
> 对应论文：DanZero+: Dominating the GuanDan Game through Reinforcement Learning（arXiv:2312.02561）
> 下载日期：2026-07-31；仅作批跑对手侧（队B client3/client4）的**推理参考**，不参与训练。

## 本目录内容（按原始仓库路径重命名，避免与现有脚本冲突）

| 文件 | 原始路径 | 说明 |
|------|---------|------|
| `wintest_torch_client1.py` | `wintest/torch/client1.py` | **完整 DanZero+ Windows 客户端**（567 维 state 编码、tribute/back 规则、决策主链路） |
| `wintest_torch_actor.py` | `wintest/torch/actor.py` | actor 进程（zmq REP），PPO 版需 `models/ppo*.pth` + `q_network.ckpt` |
| `wintest_torch_model.py` | `wintest/torch/model.py` | torch 模型定义：`MLPQNetwork`（DMC Q-net）+ `MLPActorCritic`（PPO） |
| `wintest_torch_util.py` | `wintest/torch/util.py` | 牌编码工具：`card2num` / `card2array` / `combine_handcards` |
| `wintest_torch_evaluate_*.py` | `wintest/torch/evaluate_*.py` | 训练评估脚本（本仓库不直接用） |
| `wintest_danzero_actor.py` | `wintest/danzero/actor.py` | **DMC 版 actor**：仅 `q_network.ckpt`，`sample = argmax(Q(x_batch))` |
| `wintest_danzero_model.py` | `wintest/danzero/model.py` | DMC 版 TF 模型 `GDModel`（tensorflow 1.x，本仓库不直接用） |
| `wintest_danzero_util.py` | `wintest/danzero/util.py` | 同 `wintest_torch_util.py` |
| `actor_torch_*.py` | `actor_torch/` | Linux 训练侧源码（actor/game/model/data_trans/utils），仅供理解，不直接用 |
| `README.md` | 仓库根 README | 原始 README（保留） |

## 模型权重

- **`models/danzero/q_network.ckpt`**（5.4MB，gitignore 不提交）= DMC Q-net 权重，12 个 numpy 数组：
  `[567,512]→[512]→[512,512]→[512]→…→[512,1]→[1]`，6 层 Linear（MLPQNetwork.load_tf_weights 直接加载）。
- 仓库**未提供** PPO 权重（`models/ppo*.pth` 不存在）→ 本仓库加载**DMC 版 DanZero**，决策 = 对每个合法动作
  构造 567 维 state，`argmax(Q)` 取 actIndex。

## 契约要点（对接 v1006 平台）

- 输入 567 维 state 构成（client1.prepare）：54手牌+12万能牌标志+54他人手牌+54上轮动作+54队友动作
  +54下家打出+54队友打出+54上家打出+28下家剩牌+28队友剩牌+28上家剩牌+13自级+13敌级+13现级+54当前合法动作。
- 合法动作按 `actionList` 顺序逐行编码 → `x_batch`（N×567），`argmax` 的**行索引 = actIndex**。
- `tribute`/`back` 阶段不走模型，走 client1 的规则（`tribute` / `back_action`）。
- state 依赖跨消息状态机：`history_action` / `action_seq` / `remaining` / `over` / `flag` / `mypos` /
  `other_left_hands` / `count_A` 等，须在 notify（beginning/play/episodeOver）时同步更新。
