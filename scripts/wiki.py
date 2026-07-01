#!/usr/bin/env python3
"""
LLM Wiki CLI — 基于 Karpathy 方法论的知识编译工具。

三层架构：
  raw/     → 原始资料（不可变，从 docs/ 链接）
  wiki/    → LLM 生成并维护的结构化知识库
  schema   → 规则与配置（purpose.md + schema.md）

用法：
  python scripts/wiki.py ingest     # 摄入 raw/ 中新文件
  python scripts/wiki.py query "V7 当前状态？"
  python scripts/wiki.py lint       # 健康检查
  python scripts/wiki.py status     # 查看 Wiki 状态
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ============================================================
# 配置
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
WIKI_ROOT = ROOT / "wiki"
RAW_DIR = WIKI_ROOT / "raw"
WIKI_DIR = WIKI_ROOT / "wiki"
DOT_WIKI = WIKI_ROOT / ".wiki"
CONFIG_FILE = DOT_WIKI / "config.json"
MANIFEST_FILE = DOT_WIKI / "source_manifest.json"

# 默认来源目录（raw/ 下的符号链接或直接子目录）
RAW_SOURCES = [
    ROOT / "docs" / "guandan-brain",
    ROOT / "docs" / "analysis",
    ROOT / "docs" / "knowledge",
    ROOT / "docs" / "development",
    ROOT / "docs" / "fixes",
    ROOT / "docs" / "governance",
]

# LLM 调用限制（默认值，可在 config 中覆盖）
DEFAULT_MAX_SOURCE_CHARS = 120000  # 单次摄入最大原文量
DEFAULT_BATCH_SIZE = 6             # 每次 LLM 调用处理文件数
MAX_WIKI_CHARS_PER_QUERY = 40000   # 查询时最大 Wiki 上下文


def ensure_dirs():
    """确保所有必要目录存在。"""
    for d in [RAW_DIR, WIKI_DIR, DOT_WIKI / "cache",
              WIKI_DIR / "sources", WIKI_DIR / "entities",
              WIKI_DIR / "concepts", WIKI_DIR / "queries",
              WIKI_DIR / "synthesis"]:
        d.mkdir(parents=True, exist_ok=True)


def load_config():
    """加载配置。"""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def save_config(cfg):
    """保存配置。"""
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def load_manifest():
    """加载源文件清单（SHA256 哈希表）。"""
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def save_manifest(m):
    """保存源文件清单。"""
    MANIFEST_FILE.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")


# ============================================================
# LLM 客户端
# ============================================================

def _get_llm_config():
    """获取 LLM 配置，优先环境变量。"""
    cfg = load_config()
    provider = os.environ.get("LLM_WIKI_PROVIDER", cfg.get("provider", "anthropic"))
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LLM_WIKI_API_KEY") or cfg.get("api_key", "")
    model = os.environ.get("LLM_WIKI_MODEL", cfg.get("model", "claude-sonnet-4-20250514"))
    base_url = os.environ.get("LLM_WIKI_BASE_URL", cfg.get("base_url", "")) or None
    return provider, api_key, model, base_url


def _call_llm(system_prompt: str, user_message: str, max_tokens: int = 4096) -> str:
    """调用 LLM。支持 Anthropic / OpenAI / OpenAI 兼容端点（MiniMax, DeepSeek, 智谱 等）。"""
    provider, api_key, model, base_url = _get_llm_config()

    if not api_key:
        raise RuntimeError(
            "未配置 API Key。请设置环境变量 ANTHROPIC_API_KEY / LLM_WIKI_API_KEY，或 "
            "运行 'python scripts/wiki.py config set api_key YOUR_KEY'"
        )

    if provider == "anthropic":
        try:
            import anthropic
        except ImportError:
            raise ImportError("请安装 anthropic SDK: pip install anthropic")

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = anthropic.Anthropic(**client_kwargs)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return resp.content[0].text

    elif provider in ("openai", "openai-compatible"):
        try:
            import openai
        except ImportError:
            raise ImportError("请安装 openai SDK: pip install openai")

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = openai.OpenAI(**client_kwargs)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return resp.choices[0].message.content

    else:
        raise ValueError(f"不支持的 provider: {provider}（支持 anthropic / openai / openai-compatible）")


# ============================================================
# 工具函数
# ============================================================

def _extract_json(text: str, default: dict) -> dict:
    """从 LLM 输出中提取 JSON，兼容 Markdown 代码块和尾部逗号。"""
    # 1. 去掉 Markdown 代码块包裹
    code_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if code_match:
        text = code_match.group(1)

    # 2. 尝试找到最外层花括号（非贪婪取最小层的第一层）
    brace_start = text.find('{')
    if brace_start == -1:
        return {**default, "error": "no JSON found"}
    depth = 0
    brace_end = -1
    for i in range(brace_start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                brace_end = i + 1
                break
    if brace_end == -1:
        return {**default, "error": "unmatched braces"}
    json_str = text[brace_start:brace_end]

    # 3. 去除尾部逗号（JSON 标准不允许）
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {**default, "error": str(e)}

def sha256_file(path: Path) -> str:
    """计算文件 SHA256。"""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def collect_raw_files() -> list[Path]:
    """收集 raw/ 下的所有 Markdown 文件。"""
    files = []
    for src_dir in RAW_SOURCES:
        if not src_dir.exists():
            continue
        for f in sorted(src_dir.rglob("*.md")):
            if f.is_file() and f.stat().st_size > 0:  # 跳过空文件/存根
                files.append(f)
    return files


def scan_changes() -> tuple[list[Path], list[Path], list[str]]:
    """
    扫描变化。
    返回: (新增文件, 变更文件, 删除文件路径)
    """
    manifest = load_manifest()
    current_files = set()
    new_files = []
    changed_files = []
    deleted = []

    for f in collect_raw_files():
        rel = str(f.relative_to(ROOT))
        current_files.add(rel)
        current_hash = sha256_file(f)
        if rel not in manifest:
            new_files.append(f)
        elif manifest[rel] != current_hash:
            changed_files.append(f)

    for rel in manifest:
        if rel not in current_files:
            deleted.append(rel)

    return new_files, changed_files, deleted


def update_manifest(files: list[Path]):
    """更新清单哈希。"""
    manifest = load_manifest()
    for f in files:
        manifest[str(f.relative_to(ROOT))] = sha256_file(f)
    save_manifest(manifest)


def search_wiki(query: str) -> list[dict]:
    """
    搜索 wiki/ 目录。
    返回: [{"path": "相对路径", "title": "标题", "score": 分数}, ...]
    """
    results = []
    query_lower = query.lower()
    query_terms = query_lower.split()

    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        if md_file.name in ("index.md", "log.md", "overview.md"):
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        title = ""
        title_match = re.match(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)

        # 标题匹配 +10 分
        score = 0
        if query_lower in title.lower():
            score += 10

        # 全文匹配（每命中一个词 +1 分）
        for term in query_terms:
            score += content.lower().count(term)

        if score > 0:
            rel = str(md_file.relative_to(WIKI_DIR))
            results.append({"path": rel, "title": title, "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:15]


def wikilink_to_path(wikilink: str, current_dir: Path = WIKI_DIR) -> Optional[Path]:
    """将 [[页面名]] 转为可能的文件路径。"""
    page = wikilink.strip("[]").strip()
    if not page:
        return None

    # 去掉可能的扩展名
    page = page.replace(".md", "")

    # 搜索匹配文件
    for md_file in WIKI_DIR.rglob("*.md"):
        stem = md_file.stem
        if stem.lower() == page.lower() or md_file.name.lower() == f"{page.lower()}.md":
            return md_file
        if page.lower() in stem.lower():
            return md_file
    return None


def write_page(rel_path: str, content: str):
    """写入 wiki 页面。"""
    full = WIKI_DIR / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def read_purpose() -> str:
    """读取 purpose.md。"""
    p = WIKI_ROOT / "purpose.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def read_schema() -> str:
    """读取 schema.md。"""
    p = WIKI_ROOT / "schema.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def read_index() -> str:
    """读取 wiki/index.md。"""
    p = WIKI_DIR / "index.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def page_title(path: Path) -> str:
    """从 Markdown 文件提取标题。"""
    try:
        first = path.read_text(encoding="utf-8")[:500]
        m = re.match(r'^#\s+(.+)$', first, re.MULTILINE)
        return m.group(1) if m else path.stem
    except Exception:
        return path.stem


# ============================================================
# 命令：ingest
# ============================================================

def cmd_ingest(args):
    """摄入新文件或变更文件。"""
    ensure_dirs()

    new_files, changed_files, deleted = scan_changes()
    all_to_ingest = new_files + changed_files

    if deleted:
        print(f"⚠ 检测到 {len(deleted)} 个源文件已删除: {deleted}")

    if not all_to_ingest:
        print("✓ 没有新文件或变更文件需要摄入。")
        return

    print(f"📥 待摄入: {len(new_files)} 新文件, {len(changed_files)} 变更文件\n")

    # 限制单次摄入量（可从 config 覆盖）
    cfg = load_config()
    max_source_chars = int(cfg.get("max_source_chars", DEFAULT_MAX_SOURCE_CHARS))
    batch_size = int(cfg.get("batch_size", DEFAULT_BATCH_SIZE))

    total_chars = 0
    files_to_process = []
    for f in all_to_ingest:
        size = f.stat().st_size
        total_chars += size
        files_to_process.append(f)
        if total_chars > max_source_chars:
            if len(files_to_process) == 1:
                # 第一个文件就超限，仍纳入（不能空跑）
                print(f"⚠ 首个文件已超过 {max_source_chars} 字符，但仍将处理。")
            else:
                print(f"⚠ 总大小超过 {max_source_chars} 字符，本次仅处理前 {len(files_to_process)-1} 个文件。")
                files_to_process = files_to_process[:-1]
            break

    print(f"⚙ batch_size={batch_size}, max_source_chars={max_source_chars}")
    for i in range(0, len(files_to_process), batch_size):
        batch = files_to_process[i:i + batch_size]
        _ingest_batch(batch)
        update_manifest(batch)
        print(f"  ✓ 批次 {i//batch_size + 1}/{(len(files_to_process)-1)//batch_size + 1} 完成")

    # 更新全局文件
    _update_overview()
    _update_index()

    print(f"\n✅ 摄入完成: {len(files_to_process)} 个文件已处理")
    print(f"   运行 'python scripts/wiki.py status' 查看当前状态")


def _ingest_batch(files: list[Path]):
    """摄入一批文件。"""
    sources_text = ""
    sources_info = []
    for f in files:
        rel = str(f.relative_to(ROOT))
        try:
            content = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  ✗ 无法读取 {rel}: {e}")
            continue
        # 截断过长文件
        if len(content) > 20000:
            content = content[:20000] + "\n\n...（文件过长，已截断）"
        sources_text += f"\n\n{'='*60}\n文件: {rel}\n{'='*60}\n\n{content}"
        sources_info.append({"path": rel, "chars": len(content)})

    if not sources_info:
        return

    purpose = read_purpose()
    schema = read_schema()
    existing_index = read_index()

    # 第一步：分析
    print(f"  🔍 分析 {len(sources_info)} 个文件...")
    analysis = _call_llm(
        system_prompt=f"""你是一个知识 Wiki 维护者。你的职责是阅读原始文档并生成结构化的 Markdown Wiki 页面。

## Wiki 目标
{purpose}

## Wiki 结构规则
{schema}

## 当前 Wiki 索引（已有页面）
{existing_index[:3000] if existing_index else '（空）'}

## 第一步：分析
请分析以下文档，提取以下信息（以 JSON 格式返回）：
1. key_entities: 关键实体（GUA 编号、引擎版本、模块名等）
2. key_concepts: 关键概念（策略、方法、模式等）
3. connections: 与已有 Wiki 内容的关联（引用已有页面标题）
4. tensions: 与已有知识的矛盾或需注意之处
5. structure_hints: 对 Wiki 结构的建议（哪些页面需要新建/更新）

请严格返回 JSON，不要包含其他文本。""",
        user_message=f"请分析以下文档：\n{sources_text[:50000]}",
        max_tokens=4096,
    )

    # 解析分析结果（兼容 LLM 输出不严格 JSON）
    analysis_data = _extract_json(analysis, default={
        "key_entities": [], "key_concepts": [], "connections": [],
    })
    if "error" in analysis_data:
        print(f"  ⚠ 分析 JSON 解析失败: {analysis_data['error']}，使用默认值继续")

    # 第二步：生成
    print(f"  ✍️ 生成 Wiki 页面...")
    generation = _call_llm(
        system_prompt=f"""你是一个知识 Wiki 维护者。你的职责是根据分析结果生成 Markdown Wiki 页面。

## Wiki 目标
{purpose}

## Wiki 结构规则
{schema}

## 页面类型与目录
- source-summary → wiki/sources/
- entity-gua → wiki/entities/  （GUA-xxx 缺陷条目）
- entity-engine → wiki/entities/  （M1/M3/V7 等引擎版本）
- concept → wiki/concepts/  （策略、方法、架构概念）
- synthesis → wiki/synthesis/  （跨资料综合分析）

## Frontmatter 格式
```yaml
---
type: concept
title: "页面标题"
sources:
  - docs/xxx/xxx.md
tags:
  - tag1
  - tag2
status: current
related_gua:
  - GUA-061
date: {datetime.now().strftime('%Y-%m-%d')}
---
```

## 输出格式
请为每个需要创建/更新的页面生成一个块，格式如下：
```wiki:page:路径/文件名.md
（页面的 frontmatter + 正文 Markdown）
```

路径示例：
- wiki/sources/ISSUES-summary.md
- wiki/entities/gua-061.md
- wiki/concepts/batch-evaluation.md
- wiki/synthesis/v7-current-state.md

请为每个来源文件至少创建一个 source-summary 页面。
对重要的 GUA 创建 entity 页面。
对反复出现的模式/方法创建 concept 页面。
使用 [[wikilink]] 语法建立交叉引用。""",
        user_message=f"""分析结果：
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

原始来源文件信息：
{json.dumps(sources_info, ensure_ascii=False)}

请生成 Wiki 页面。记得使用 @@WIKI:PAGE:路径 分隔每个页面。""",
        max_tokens=8192,
    )

    # 解析生成的页面并写入
    _save_generated_pages(generation, [s["path"] for s in sources_info])
    _log_operation("ingest", sources_info)


def _save_generated_pages(generation: str, source_paths: list[str]):
    """解析 LLM 生成的页面并写入文件。"""
    # 匹配 ```wiki:page:路径 或 @@WIKI:PAGE:路径 格式
    pattern = r'(?:```wiki:page:|@@WIKI:PAGE:)\s*(\S+)\s*\n(.*?)(?=(?:```wiki:page:|@@WIKI:PAGE:|\Z))'
    matches = list(re.finditer(pattern, generation, re.DOTALL))

    created = []
    for m in matches:
        path = m.group(1).strip()
        # 规范化路径：去掉 LLM 可能添加的 wiki/ 或 wiki\ 前缀（WIKI_DIR 已是 wiki/wiki/）
        path = re.sub(r'^(wiki[/\\])+', '', path)
        content = m.group(2).strip()

        # 清理末尾可能的 ```
        content = re.sub(r'\n```\s*$', '', content)

        # 确保 frontmatter 中的 sources 字段正确
        if not re.search(r'^sources:', content, re.MULTILINE):
            sources_yaml = "\n".join([f"  - {s}" for s in source_paths])
            content = content.replace(
                "---\n",
                f"---\nsources:\n{sources_yaml}\n",
                1,
            )

        write_page(path, content + "\n")
        created.append(path)
        print(f"    + {path}")

    # 如果没有匹配到，整段视为一个 overview 页面
    if not matches and len(generation) > 100:
        write_page("overview.md", generation + "\n")
        print(f"    + overview.md (未匹配到分页标记，整体写入)")


# ============================================================
# 命令：query
# ============================================================

def cmd_query(args):
    """查询 Wiki。"""
    ensure_dirs()
    query_text = " ".join(args.query)
    print(f"🔍 查询: {query_text}\n")

    # 搜索 Wiki
    search_results = search_wiki(query_text)
    if not search_results:
        print("未找到相关 Wiki 页面。尝试运行 'python scripts/wiki.py ingest' 先构建知识库。")
        return

    print(f"📄 找到 {len(search_results)} 个相关页面:")

    # 组装上下文
    context = ""
    total_chars = 0
    for i, r in enumerate(search_results[:10], 1):
        page_path = WIKI_DIR / r["path"]
        try:
            content = page_path.read_text(encoding="utf-8")
        except Exception:
            continue
        if total_chars + len(content) > MAX_WIKI_CHARS_PER_QUERY:
            content = content[:MAX_WIKI_CHARS_PER_QUERY - total_chars] + "\n...(截断)"
        context += f"\n\n--- 页面 [{i}]: {r['path']} (分数:{r['score']}) ---\n{content}"
        total_chars += len(content)
        print(f"  [{i}] {r['path']} (分数:{r['score']})")

    # LLM 回答（若 API key 可用）
    _, api_key, _, _ = _get_llm_config()
    if api_key:
        purpose = read_purpose()
        answer = _call_llm(
            system_prompt=f"""你是一个知识 Wiki 查询助手。根据 Wiki 内容回答问题。

## Wiki 目标
{purpose}

## 规则
- 引用页面时使用 [{{n}}] 格式（n 是页面编号）
- 如果 Wiki 中没有足够信息，请诚实说明
- 回答简洁、直接、有层次""",
            user_message=f"## 用户问题\n{query_text}\n\n## 相关 Wiki 页面\n{context}",
            max_tokens=2048,
        )

        print(f"\n{'='*60}\n📝 回答:\n{'='*60}")
        print(answer)
    else:
        print(f"\n{'='*60}\n💡 未配置 LLM API Key，仅显示搜索结果。")
        print("   设置 export ANTHROPIC_API_KEY=... 可启用 AI 总结。")
        answer = "（未配置 API Key，无 AI 总结）"

    # 可选：保存到 queries
    ts = datetime.now().strftime("%m%d-%H%M")
    safe_q = re.sub(r'[^a-zA-Z\u4e00-\u9fff]+', '-', query_text)[:40]
    query_file = WIKI_DIR / "queries" / f"query-{ts}-{safe_q}.md"
    query_file.write_text(
        f"---\ntype: query-answer\ntitle: \"{query_text[:80]}\"\ndate: {datetime.now().strftime('%Y-%m-%d')}\nsources:\n"
        + "\n".join(f"  - wiki/{r['path']}" for r in search_results[:10])
        + f"\n---\n\n# {query_text[:80]}\n\n{answer}\n",
        encoding="utf-8",
    )
    print(f"\n💾 已保存: {query_file.relative_to(ROOT)}")


# ============================================================
# 命令：lint
# ============================================================

def cmd_lint(args):
    """健康检查。"""
    ensure_dirs()
    issues = []

    # 1. 断链检测
    print("🔗 检测断链...")
    all_wikilinks = set()
    for md_file in WIKI_DIR.rglob("*.md"):
        if md_file.name in ("index.md", "log.md", "overview.md"):
            continue
        content = md_file.read_text(encoding="utf-8")
        for m in re.finditer(r'\[\[(.+?)\]\]', content):
            all_wikilinks.add(m.group(1))

    for link in sorted(all_wikilinks):
        # 剥去 |label 与 #anchor（wikilink_to_path 不处理这两者）
        stripped = link.split("|", 1)[0].split("#", 1)[0]
        if wikilink_to_path(stripped) is None:
            issues.append(("断链", f"[[{link}]] 无对应页面"))

    # 2. 孤立页面
    print("🏝️ 检测孤立页面...")
    linked_pages = set()
    for md_file in WIKI_DIR.rglob("*.md"):
        if md_file.name in ("index.md", "log.md", "overview.md"):
            continue
        content = md_file.read_text(encoding="utf-8")
        for m in re.finditer(r'\[\[(.+?)\]\]', content):
            target = wikilink_to_path(m.group(1))
            if target:
                linked_pages.add(str(target.relative_to(WIKI_DIR)))

    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        if md_file.name in ("index.md", "log.md", "overview.md"):
            continue
        rel = str(md_file.relative_to(WIKI_DIR))
        if rel not in linked_pages:
            issues.append(("孤立", f"{rel} (入链 ≤ 0)"))

    # 3. 缺少 frontmatter
    print("📋 检测缺少 frontmatter 的页面...")
    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        if md_file.name in ("index.md", "log.md", "overview.md"):
            continue
        content = md_file.read_text(encoding="utf-8")
        rel = str(md_file.relative_to(WIKI_DIR))
        if not content.startswith("---"):
            issues.append(("格式", f"{rel} 缺少 YAML frontmatter"))
        else:
            # 检查必填字段
            end = content.find("---", 3)
            fm = content[3:end] if end > 0 else ""
            for field in ["type", "title", "date"]:
                if not re.search(rf'^{field}:', fm, re.MULTILINE):
                    issues.append(("格式", f"{rel} frontmatter 缺少 '{field}'"))

    # 4. 来源文件存在性（仅检查 sources 列表项，不误吞 tags/related_gua）
    print("📂 检测来源引用...")
    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        if md_file.name in ("index.md", "log.md", "overview.md"):
            continue
        content = md_file.read_text(encoding="utf-8")
        rel = str(md_file.relative_to(WIKI_DIR))
        if "sources:" in content:
            lines = content.split("\n")
            in_sources = False
            sources = []
            for line in lines:
                if line.startswith("sources:"):
                    in_sources = True
                    continue
                if in_sources:
                    if line.startswith("  - "):
                        sources.append(line[4:].strip())
                    elif re.match(r'^[a-zA-Z_]', line.strip()) and not line.startswith(" "):
                        break  # 下一个顶层 YAML key，停止收集
            for src in sources:
                if not (ROOT / src).exists() and not (WIKI_DIR / src).exists():
                    issues.append(("来源", f"{rel}: 引用 '{src}' 不存在"))

    # 输出结果
    print(f"\n{'='*60}")
    if issues:
        print(f"⚠ 发现 {len(issues)} 个问题:\n")
        for category, detail in sorted(issues, key=lambda x: x[0]):
            print(f"  [{category}] {detail}")
    else:
        print("✅ Wiki 健康，未发现问题。")

    print(f"\n总计: 断链 {sum(1 for c,_ in issues if c=='断链')} | "
          f"孤立 {sum(1 for c,_ in issues if c=='孤立')} | "
          f"格式 {sum(1 for c,_ in issues if c=='格式')} | "
          f"来源 {sum(1 for c,_ in issues if c=='来源')}")


# ============================================================
# 命令：status
# ============================================================

def cmd_status(args):
    """查看 Wiki 状态。"""
    ensure_dirs()
    manifest = load_manifest()

    all_files = collect_raw_files()
    new, changed, deleted = scan_changes()

    # Wiki 页面统计
    wiki_pages = list(WIKI_DIR.rglob("*.md"))
    entity_count = len(list((WIKI_DIR / "entities").glob("*.md")))
    concept_count = len(list((WIKI_DIR / "concepts").glob("*.md")))
    source_count = len(list((WIKI_DIR / "sources").glob("*.md")))
    synth_count = len(list((WIKI_DIR / "synthesis").glob("*.md")))
    query_count = len(list((WIKI_DIR / "queries").glob("*.md")))

    print("=" * 60)
    print("LLM Wiki 状态")
    print("=" * 60)
    print(f"来源文件: {len(manifest)} 已追踪, {len(new)} 新, {len(changed)} 变更, {len(deleted)} 删除")
    print(f"Wiki 页面: {len(wiki_pages)} 总计")
    print(f"  entities/ : {entity_count}")
    print(f"  concepts/ : {concept_count}")
    print(f"  sources/  : {source_count}")
    print(f"  synthesis/: {synth_count}")
    print(f"  queries/  : {query_count}")

    if new or changed:
        print(f"\n⚠ 有 {len(new) + len(changed)} 个源文件待摄入。运行: python scripts/wiki.py ingest")
    else:
        print("\n✅ Wiki 已是最新。")


# ============================================================
# 命令：config
# ============================================================

def cmd_config(args):
    """配置 Wiki。"""
    cfg = load_config()
    if args.config_action == "show":
        safe_cfg = {k: v for k, v in cfg.items() if k != "api_key"}
        if "api_key" in cfg:
            safe_cfg["api_key"] = "***" + cfg["api_key"][-4:] if len(cfg["api_key"]) > 4 else "***"
        print(json.dumps(safe_cfg, indent=2, ensure_ascii=False))
    elif args.config_action == "set" and args.key and args.value:
        cfg[args.key] = args.value
        save_config(cfg)
        print(f"✓ {args.key} = {args.value if args.key != 'api_key' else '***'}")
    else:
        print("用法: python scripts/wiki.py config show")
        print("      python scripts/wiki.py config set provider anthropic")
        print("      python scripts/wiki.py config set model claude-sonnet-4-20250514")
        print("      python scripts/wiki.py config set batch_size 8")
        print("      python scripts/wiki.py config set max_source_chars 200000")


# ============================================================
# 命令：init
# ============================================================

def cmd_init(args):
    """初始化 Wiki 目录。"""
    ensure_dirs()

    # 写入 index.md
    if not (WIKI_DIR / "index.md").exists():
        (WIKI_DIR / "index.md").write_text(
            "# Wiki Index\n\n"
            "> 由 LLM 维护。运行 `python scripts/wiki.py ingest` 填充。\n\n"
            "## Entities (GUA / 引擎 / 模块)\n\n"
            "## Concepts (概念 / 方法)\n\n"
            "## Source Summaries (资料摘要)\n\n"
            "## Synthesis (综合分析)\n",
            encoding="utf-8",
        )

    # 写入 log.md
    if not (WIKI_DIR / "log.md").exists():
        (WIKI_DIR / "log.md").write_text(
            "# Wiki Log\n\n"
            f"| 时间 | 操作 | 文件 |\n"
            f"|------|------|------|\n"
            f"| {datetime.now().strftime('%Y-%m-%d %H:%M')} | init | — |\n",
            encoding="utf-8",
        )

    # 写入 overview.md
    if not (WIKI_DIR / "overview.md").exists():
        (WIKI_DIR / "overview.md").write_text(
            "# Wiki Overview\n\n"
            "> 全局概要。运行 `python scripts/wiki.py ingest` 后自动生成。\n",
            encoding="utf-8",
        )

    print("✅ Wiki 初始化完成!")
    print(f"   目录: {WIKI_ROOT}")
    print(f"   来源: {', '.join(str(s) for s in RAW_SOURCES)}")
    print(f"\n   下一步: python scripts/wiki.py ingest")


# ============================================================
# 内部辅助
# ============================================================

def _update_overview():
    """更新 wiki/overview.md。"""
    entity_pages = list((WIKI_DIR / "entities").glob("*.md"))
    concept_pages = list((WIKI_DIR / "concepts").glob("*.md"))
    source_pages = list((WIKI_DIR / "sources").glob("*.md"))
    synth_pages = list((WIKI_DIR / "synthesis").glob("*.md"))

    lines = [
        "# Wiki Overview",
        "",
        f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"## 统计",
        f"- Entities: {len(entity_pages)}",
        f"- Concepts: {len(concept_pages)}",
        f"- Sources: {len(source_pages)}",
        f"- Synthesis: {len(synth_pages)}",
        "",
        "## Entity 页面",
    ]
    for p in sorted(entity_pages):
        title = page_title(p)
        lines.append(f"- [[{p.stem}]] — {title}")

    lines.extend(["", "## Concept 页面"])
    for p in sorted(concept_pages):
        title = page_title(p)
        lines.append(f"- [[{p.stem}]] — {title}")

    lines.extend(["", "## Synthesis 页面"])
    for p in sorted(synth_pages):
        title = page_title(p)
        lines.append(f"- [[{p.stem}]] — {title}")

    (WIKI_DIR / "overview.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_index():
    """更新 wiki/index.md。"""
    index = (WIKI_DIR / "index.md")
    content = index.read_text(encoding="utf-8") if index.exists() else "# Wiki Index\n\n"

    # 简单追加新页面链接（已有 LLM 生成的 index 时，保持其内容）
    if len(content) < 200:
        # 只有初始化内容时，从 overview 重建
        overview = (WIKI_DIR / "overview.md").read_text(encoding="utf-8")
        index.write_text(overview, encoding="utf-8")


def _log_operation(op: str, sources_info: list[dict]):
    """记录操作到 log.md。"""
    log_file = WIKI_DIR / "log.md"
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    files = ", ".join(s["path"].split("/")[-1] for s in sources_info[:3])
    if len(sources_info) > 3:
        files += f" (+{len(sources_info)-3})"
    entry = f"| {ts} | {op} | {files} |\n"

    if log_file.exists():
        content = log_file.read_text(encoding="utf-8") + entry
    else:
        content = "# Wiki Log\n\n| 时间 | 操作 | 文件 |\n|------|------|------|\n" + entry
    log_file.write_text(content, encoding="utf-8")


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="LLM Wiki CLI — 知识编译工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/wiki.py init           # 初始化 Wiki 目录
  python scripts/wiki.py ingest         # 摄入文档变化
  python scripts/wiki.py query "V7 当前状态是什么？"
  python scripts/wiki.py lint           # 健康检查
  python scripts/wiki.py status         # 查看状态
  python scripts/wiki.py config show    # 查看配置
        """,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="初始化 Wiki 目录")
    sub.add_parser("ingest", help="摄入新/变更文档")
    sub.add_parser("lint", help="Wiki 健康检查")
    sub.add_parser("status", help="查看 Wiki 状态")

    query_parser = sub.add_parser("query", help="查询 Wiki")
    query_parser.add_argument("query", nargs="+", help="查询文本")

    config_parser = sub.add_parser("config", help="管理配置")
    config_parser.add_argument("config_action", choices=["show", "set"])
    config_parser.add_argument("key", nargs="?", help="配置键")
    config_parser.add_argument("value", nargs="?", help="配置值")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "lint":
        cmd_lint(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
