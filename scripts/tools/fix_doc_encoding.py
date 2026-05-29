#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量修复 GBK/UTF-8 混用导致的文档乱码（分块 gb18030→utf-8 + 安全短语修补）。"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 仅含「二层乱码」特征字，避免误改已是正常中文的片段
PHRASE_FIXES: list[tuple[str, str]] = sorted(
    [
        ("掼蛋AI客户绔鍩虹架构鏂规", "掼蛋AI客户端基础架构方案"),
        ("掼蛋AI客户绔架构鏂规", "掼蛋AI客户端架构方案"),
        ("客户绔鍩虹架构鏂规", "客户端基础架构方案"),
        ("客户绔架构鏂规", "客户端架构方案"),
        ("客户绔鍩虹", "客户端基础"),
        ("客户绔", "客户端"),
        ("鍩虹架构", "基础架构"),
        ("鍩虹", "基础"),
        ("架构鏂规堬", "架构方案"),
        ("架构鏂规", "架构方案"),
        ("鏂规堬", "方案"),
        ("鏂规", "方案"),
        ("鏈文档", "本文档"),
        ("基纭架构", "基础架构"),
        ("基纭", "基础"),
        ("寮鍙戠﹀悎", "开发符合"),
        ("南京閭电大学", "南京邮电大学"),
        ("閭电大学", "邮电大学"),
        ("鐨勫㈡埛绔", "的客户端"),
        ("㈡埛绔", "客户端"),
        ("鑷动出牌", "自动出牌"),
        ("鑷动", "自动"),
        ("鏀持自", "支持自"),
        ("鏀持", "支持"),
        ("鎴戝瑰紙", "对弈和"),
        ("数鎹收集", "数据收集"),
        ("数鎹", "数据"),
        ("架鏋勮捐", "架构设计"),
        ("鏋勮捐", "构设计"),
        ("鐩鏍", "目标"),
        ("项目鐩鏍", "项目目标"),
        ("全阶娈", "全阶段"),
        ("知识搴", "知识库"),
        ("详细鍐呭", "详细内容"),
        ("鎶鏈选型", "技术选型"),
        ("浜屻佺郴统架鏋勮", "二、系统架构设计"),
        ("分灞傝捐", "分层设计"),
        ("涓夈佹牳心模鍧楄", "三、核心模块设计"),
        ("鐘舵佺＄悊鍣", "状态管理器"),
        ("鐘舵佺壒征编码器", "状态特征编码器"),
        ("知识库架鏋勮", "知识库架构设计"),
        ("鎶巧库", "技巧库"),
        ("知识妫索", "知识检索"),
        ("ƒ̨", "平台"),
        ("平台鐨", "平台的"),
        ("一等奖代码优绉", "一等奖代码优秀"),
        ("优绉特点", "优秀特点"),
        ("东南大瀛", "东南大学"),
        ("涓绛夊栦", "一等奖"),
        ("代碼", "代码"),
        ("璁捐′", "设计"),
        ("浼樼鐐", "优点"),
        ("启绀", "启示"),
        ("模块划鍒", "模块划分"),
        ("负璐", "负责"),
        ("消鎭", "消息"),
        ("由锛", "由："),
        ("绠洁", "简洁"),
        ("动浣滈", "动作"),
        ("组鍚", "组合"),
        ("决绛", "决策"),
        ("历ʷ", "历史"),
        ("专門", "专门"),
        ("鐢", "用"),
        ("存槑", "说明"),
        ("掼铔", "掼蛋"),
        ("規則", "规则"),
        ("方案紝", "方案，"),
        ("**目标**锛", "**目标**："),
        ("**优点**锛", "**优点**："),
        ("**代码体现**锛", "**代码体现**："),
        ("锛", "："),
        ("鍙扩展", "可扩展"),
        ("涓、项鐩概述", "一、项目概述"),
        ("编程璇瑷", "编程语言"),
        ("蹇速", "快速"),
        ("WebSocket搴", "WebSocket库"),
        ("标准库锛", "标准库）"),
        ("调试锛", "调试）"),
        ("请求锛", "请求）"),
        ("参与锛", "参与）"),
        ("可选（閭浠", "可选（邮件"),
        ("格寮忚佹眰", "格式要求"),
        ("同时参与**锛", "同时参与**："),
        ("连接**锛", "连接**："),
        ("系统架构设计捐", "系统架构设计"),
        ("核心模块设计捐", "核心模块设计"),
        ("分层设计★級", "分层设计）"),
        ("应用灞", "应用层"),
        ("决策灞", "决策层"),
        ("逻辑灞", "逻辑层"),
        ("通信灞", "通信层"),
        ("数据灞", "数据层"),
        ("信息监控灞", "信息监控层"),
        ("主程序入鍙", "主程序入口"),
        ("平台鍔ㄦ佹姄鍙", "平台动态抓取"),
        ("知识库查璇", "知识库查询"),
        ("纭编码锛", "硬编码）"),
        ("内存加载锛", "内存加载）"),
        ("按闇鏌ヨ锛", "按需查询）"),
        ("知识妫绱与缓瀛", "知识检索与缓存"),
        ("鐘舵佺＄悊", "状态管理"),
        ("消息璺用", "消息路由"),
        ("缁熻″垎鏋", "统计分析"),
        ("鏈地", "本地"),
        ("灞域网", "局域网"),
        ("维鎶", "维护"),
        ("恢澶", "恢复"),
        ("一等奖唬码", "一等奖代码"),
        ("一绛夊栦唬码", "一等奖代码"),
        ("设计紭绉", "设计优秀"),
        ("浼樼特点", "优秀特点"),
        ("鐩褰", "目录"),
        ("使用ㄨ说明涔", "使用说明书"),
        ("掼蛋嬭勫垯", "掼蛋规则"),
        ("决策栭昏緫", "决策逻辑"),
        ("动作夋嫨", "动作选择"),
        ("组合堛", "组合"),
        ("墿余", "剩余"),
        ("计算绛", "计算等"),
        ("完整寮发指鍗", "完整开发指南"),
        ("寮发指鍗", "开发指南"),
        ("鎶鏈实现", "技术实现"),
        ("璁练方娉", "训练方法"),
        ("鏈佳实璺", "最佳实践"),
        ("参赛指鍗", "参赛指南"),
        ("寮发", "开发"),
        ("鎵有", "所有"),
        ("涓撳剁煡识", "专家知识"),
        ("堛", "）"),
        ("指鍗", "指南"),
        ("平鍙", "平台"),
        ("技鏈", "技术"),
        ("鎸囧", "指导"),
        ("确淇", "确保"),
        ("﹀悎", "符合"),
        ("璁捐★", "设计"),
        ("鍣ㄥ勭悊", "器处理"),
        ("绗涓部分", "第一部分"),
        ("系缁", "系统"),
        ("（`datetime.now()`：", "（`datetime.now()`）"),
        ("支持自对弈和和数据", "支持自我对弈和数据"),
        ("鍙选", "可选"),
        ("閭浠", "邮件"),
        ("鐜澧", "环境"),
        ("氱1銆3涓", "第 1、3 号"),
        ("绗2銆4涓", "第 2、4 号"),
        ("为一闃", "为另一队"),
    ],
    key=lambda x: -len(x[0]),
)

MOJIBAKE_MARKERS = (
    "鎺艰泲",
    "瀹㈡埛",
    "鏋舵瀯",
    "鍐崇瓥",
    "绔鍩",
    "鏂规",
    "閭电",
    "鐨勫",
    "鑷动",
    "鏀持",
    "鎴戝",
    "数鎹",
    "鏋勮",
    "鐩鏍",
    "娈",
    "搴",
    "鍐呭",
    "鎶鏈",
    "灞傝",
    "鐘舵",
    "锟斤拷",
)

# 框线字符二次乱码
BOX_FIXES = [
    ("┌─鈹", "├──"),
    ("└─鈹", "└──"),
    ("鈹", "│"),
    ("鈫", "↓"),
]


def decode_mojibake_chunked(text: str, max_window: int = 16) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ord(ch) < 128:
            out.append(ch)
            i += 1
            continue
        matched = False
        for w in range(min(max_window, n - i), 0, -1):
            chunk = text[i : i + w]
            try:
                decoded = chunk.encode("gb18030").decode("utf-8")
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
            if decoded:
                out.append(decoded)
                i += w
                matched = True
                break
        if not matched:
            out.append(ch)
            i += 1
    return "".join(out)


def apply_phrase_fixes(text: str) -> str:
    for bad, good in PHRASE_FIXES:
        if bad in text:
            text = text.replace(bad, good)
    for bad, good in BOX_FIXES:
        text = text.replace(bad, good)
    # 清理误叠字
    text = re.sub(r"器{2,}", "器", text)
    text = re.sub(r"端{2,}", "端", text)
    text = re.sub(r"模块块", "模块", text)
    return text


def fix_text(text: str) -> str:
    once = decode_mojibake_chunked(text)
    return apply_phrase_fixes(once)


def looks_mojibake(text: str) -> bool:
    sample = text[:8000]
    return any(m in sample for m in MOJIBAKE_MARKERS)


DEFAULT_TARGETS = [
    "docs/architecture/掼蛋AI客户端架构方案.md",
    "docs/development/掼蛋AI完整开发指南.md",
    "docs/knowledge/掼蛋AI知识应用框架.md",
    "docs/competition/一等奖代码优秀特点分析.md",
    "docs/knowledge/知识库格式化方案.md",
    "docs/development/DEVELOPMENT_RULES.md",
    "docs/training/REPLAY_TRAINING_GUIDE.md",
]


def process_file(path: Path, dry_run: bool, phrases_only: bool = False) -> tuple[bool, str]:
    raw = path.read_text(encoding="utf-8")
    if phrases_only:
        fixed = apply_phrase_fixes(raw)
    elif looks_mojibake(raw):
        fixed = fix_text(raw)
    else:
        return False, "skip (no mojibake markers)"
    if fixed == raw:
        return False, "unchanged"
    if not dry_run:
        path.write_text(fixed, encoding="utf-8", newline="\n")
    rep = fixed.count("\ufffd")
    return True, f"fixed (U+FFFD={rep})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="文件路径（默认清单）")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--phrases-only",
        action="store_true",
        help="仅做短语修补（用于已跑过 chunked 解码的文件）",
    )
    args = parser.parse_args()

    targets = [ROOT / p for p in (args.paths or DEFAULT_TARGETS)]
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] fix_doc_encoding")
    for path in targets:
        if not path.is_file():
            print(f"  MISSING {path.relative_to(ROOT)}")
            continue
        changed, msg = process_file(path, args.dry_run, args.phrases_only)
        flag = "OK" if changed else "—"
        print(f"  [{flag}] {path.relative_to(ROOT)}: {msg}")


if __name__ == "__main__":
    main()
