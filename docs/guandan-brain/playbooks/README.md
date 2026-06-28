# 开发 Playbook（典范 / 模板）

> **用途**：把「做过且验证有效」的开发经验升格为可复用模板，供人类与 Agent 照抄。  
> **与工作流分工**：[`工作流.md`](../工作流.md) = 步骤 SOP；**本目录 = 方法论 + 反例 + 验证命令**。  
> **与 GUA 分工**：`issues/GUA-xxx-completion.md` = 个案关单；**Playbook = 可跨 GUA 复用的模式**。

---

## 索引

| ID | 标题 | 场景 |
|----|------|------|
| [PB-001](./PB-001-gua072-bomb-break-timing.md) | GUA-072 拆炸：**时序押后**优于改阈值 | 组牌 / 多策略分支 / 保核心资源 |

---

## 升格条件（何时写 Playbook）

满足 **任一** 即可新建 PB-xxx（见工作流 **WF-11**）：

1. 同类问题会再出现  
2. 有可复现验证命令（pytest / `check_*.py`）  
3. 有明确 **反例**（不要做什么）  
4. 人类或 Agent 定音：「以后照这个来」

---

## 新建 Playbook 模板

复制 [`_template.md`](./_template.md) → `PB-xxx-简短英文名.md`，在本 README 索引表追加一行。

升格后可选：`python scripts/wiki.py ingest`（便于 `wiki query` 检索）。
