"""
Qoder SDK 派单 v2：精简版复审 V7-实施方案.md
- 只读 V7-实施方案.md
- 8 补丁逐项验证（Q1-Q8）+ 硬约束 7 项 + 总体结论
- 不要求协同深挖、不要求事实性核查
- 后台跑，避免 terminal 超时
"""
import anyio
import sys
from pathlib import Path
from qoder_agent_sdk import (
    QoderAgentOptions,
    qodercli_auth,
    query,
    AssistantMessage,
    TextBlock,
)


SYSTEM_PROMPT = """你是 V7-实施方案.md 的复审 Agent。

【只读 V7-实施方案.md】+ V7-方案评审.md §7（已通过的 11 实施约束 + 升格硬约束）
【绝不能写 / 跑命令 / 联网】
【8 补丁清单】
- S1: GUA-037a 维度 120→124；actionList 15 维后移 037b 拼接层
- S2: §0.2 表格 037a 工作量 0.8→1 迭代
- S3: §0.2 标题「9 条」统一（含 S3 注释）
- S4: §4 依赖图补 2 节点（开工握手 + 30 局 baseline）+ 037b‖038 并行 + 串行/关键路径对比
- S5: GUA-039b 评估两阶段（fallback baseline + PPO 收敛对照）
- S6: GUA-040【交付】加 1 句"不依赖 M3 权重/数据管理链路"
- S7: GUA-042 估 0.3→0.4-0.5 迭代
- + src.train: §1.2 升格表后加列（src.train 临时允许 + src.m.m1/m2 禁止）

【输出】
- 中文
- 顶层：Q1-Q8 逐项答（每题 1-2 句）+ 7 项硬约束自检 + 总体结论（通过/需修订）
- 不超过 60 行
"""


async def main() -> int:
    repo_root = Path(r"C:\yifeGDBOT")
    target = repo_root / "docs" / "guandan-brain" / "V7-实施方案.md"

    try:
        auth = qodercli_auth()
        print("[auth] OK (reused Qoder IDE state)")
    except Exception as e:
        print(f"[auth] FAIL: {e}", file=sys.stderr)
        return 2

    options = QoderAgentOptions(
        auth=auth,
        cwd=repo_root,
        max_turns=1,
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["Read", "Grep", "Glob"],
        disallowed_tools=["Edit", "Write", "Bash", "WebFetch", "WebSearch"],
        permission_mode="default",
    )

    prompt = (
        f"复审 {target} 的 8 补丁。\n"
        f"对每个补丁：1) 到位情况（到位/部分/缺失）2) 是否引入新矛盾（是/否）\n"
        f"最后给 7 项硬约束自检 + 总体结论（通过/需修订）。\n"
        f"不超过 60 行。"
    )
    print(f"[target] {target.name}")
    print("[streaming]---")

    msg_count = 0
    text_chunks = []
    async for message in query(prompt=prompt, options=options):
        msg_count += 1
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_chunks.append(block.text)
        else:
            print(f"[msg {msg_count}] {type(message).__name__}")

    print("---")
    if text_chunks:
        for chunk in text_chunks:
            print(chunk)
    else:
        print("[no text]", file=sys.stderr)

    print(f"\n[done] messages={msg_count}, chunks={len(text_chunks)}")
    return 0


if __name__ == "__main__":
    sys.exit(anyio.run(main))
