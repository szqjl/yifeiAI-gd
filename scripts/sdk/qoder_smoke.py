"""
Qoder Agent SDK 冒烟测试
- 读 docs/guandan-brain/V7-实施方案.md
- 问 3 个问题验证流式响应
- 不开 GUI，进程内 async iterator
"""
import anyio
import sys
from pathlib import Path
from qoder_agent_sdk import (
    QoderAgentOptions,
    qodercli_auth,
    access_token_from_env,
    query,
    AssistantMessage,
    TextBlock,
)


async def main() -> int:
    repo_root = Path(r"C:\yifeGDBOT")
    target = repo_root / "docs" / "guandan-brain" / "V7-实施方案.md"

    # 优先用 PAT（环境变量），无则回退本机 qodercli 登录态
    import os
    if os.environ.get("QODER_PERSONAL_ACCESS_TOKEN"):
        auth = access_token_from_env()
        print("[auth] using QODER_PERSONAL_ACCESS_TOKEN")
    else:
        try:
            auth = qodercli_auth()
            print("[auth] using local qodercli login (Qoder IDE)")
        except Exception as e:
            print(f"[auth] FAIL: {e}", file=sys.stderr)
            print("  → 需先在桌面 Qoder 登录，或设 QODER_PERSONAL_ACCESS_TOKEN", file=sys.stderr)
            return 2

    options = QoderAgentOptions(
        auth=auth,
        cwd=repo_root,
        max_turns=1,
        system_prompt="你是只读分析助手。简洁、精确；不修改任何文件。",
    )

    prompt = (
        f"只读 {target} §0.2 GUA 清单，回复（每条一行）：\n"
        f"1) GUA 几条\n"
        f"2) 037a 估迭代多少\n"
        f"3) state_牌态维度是多少（看 §2 GUA-037a 任务块）\n"
    )
    print(f"[prompt] {prompt.strip()}\n[streaming]\n---")

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
        print("[assistant]")
        for chunk in text_chunks:
            print(chunk)
    else:
        print("[no text returned]", file=sys.stderr)

    print(f"\n[done] messages={msg_count}, text_blocks={len(text_chunks)}")
    return 0


if __name__ == "__main__":
    sys.exit(anyio.run(main))
