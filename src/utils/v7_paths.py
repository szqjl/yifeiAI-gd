# -*- coding: utf-8 -*-
"""V7 路径解析：环境变量 > config/v7_paths.yaml > 仓库内候选路径。"""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
V7_PATHS_FILE = REPO_ROOT / "config" / "v7_paths.yaml"

LALALA_REFERENCE_REL = "reference/lalala"
LALALA_ASCII_REL = "guandan_offline_v1006/lalala"
LALALA_LEGACY_REL = "guandan_offline_v1006/一等奖-东南大学-李菁-lalala-人机大赛"
LALALA_CORE_FILES = ("state.py", "action.py", "utils.py")

DEFAULT_SERVER_CANDIDATES = (
    "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe",
    "guandan_offline_v1006/windows/guandan_offline_v1006.exe",
)

DEFAULT_LALALA_CANDIDATES = (
    LALALA_ASCII_REL,
    LALALA_REFERENCE_REL,
    LALALA_LEGACY_REL,
)
DEFAULT_MODEL_CANDIDATES = (
    "models/bc_model_ultimate_win_rate.pth",
    "models/v-nn/bc_model_ultimate_win_rate.pth",
)


def _expand_repo(token: str, repo_root: Optional[Path] = None) -> str:
    root = repo_root or REPO_ROOT
    return token.replace("%REPO_ROOT%", str(root)).replace("/", os.sep)


def _first_existing(paths: Iterable[str | Path]) -> Optional[Path]:
    for raw in paths:
        p = Path(raw)
        if p.is_file() or p.is_dir():
            return p
    return None


@lru_cache(maxsize=1)
def load_v7_paths_config() -> Dict[str, Any]:
    if not V7_PATHS_FILE.is_file():
        return {}
    try:
        import yaml

        with open(V7_PATHS_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_repo_root() -> Path:
    return REPO_ROOT


def resolve_v7_path(
    key: str,
    *,
    env_var: str = "",
    yaml_key: str = "",
    candidates: Optional[List[str]] = None,
    must_exist: bool = True,
    repo_root: Optional[Path] = None,
) -> str:
    """解析 V7 相关路径。优先级：环境变量 > yaml > 首个存在的候选 > yaml/候选字符串。"""
    root = repo_root or REPO_ROOT
    cfg = load_v7_paths_config()

    if env_var:
        env_val = os.environ.get(env_var, "").strip()
        if env_val:
            return env_val

    yk = yaml_key or key
    yaml_val = str(cfg.get(yk, "") or "").strip()
    if yaml_val:
        expanded = _expand_repo(yaml_val, root)
        if not must_exist or Path(expanded).exists():
            return expanded

    rel_candidates = candidates or []
    for rel in rel_candidates:
        p = root / Path(rel)
        if p.is_file() or p.is_dir():
            return str(p)

    if yaml_val:
        return _expand_repo(yaml_val, root)
    if rel_candidates:
        return str(root / Path(rel_candidates[0]))
    return ""


def get_server_exe(repo_root: Optional[Path] = None) -> str:
    return resolve_v7_path(
        "server_exe",
        env_var="SERVER_EXE",
        candidates=list(DEFAULT_SERVER_CANDIDATES),
        repo_root=repo_root,
    )


def get_server_argv(repo_root: Optional[Path] = None) -> str:
    cfg = load_v7_paths_config()
    return str(cfg.get("server_args", "12") or "12").strip()


def get_server_command(repo_root: Optional[Path] = None) -> str:
    return f"{get_server_exe(repo_root=repo_root)} {get_server_argv(repo_root=repo_root)}"


def _lalala_dir_usable(path: Path) -> bool:
    return path.is_dir() and all((path / name).is_file() for name in LALALA_CORE_FILES)


def sync_lalala_to_reference(repo_root: Optional[Path] = None) -> Path:
    """
    将 lalala 核心 py 复制到 reference/lalala（纯 ASCII 路径）。
    源目录默认为含中文名的官方包路径。
    """
    root = repo_root or REPO_ROOT
    dest = root / LALALA_REFERENCE_REL
    dest.mkdir(parents=True, exist_ok=True)

    env_src = os.environ.get("LALALA_SOURCE_DIR", "").strip()
    if env_src:
        source = Path(env_src)
    else:
        for rel in (LALALA_ASCII_REL, LALALA_LEGACY_REL):
            candidate = root / rel
            if _lalala_dir_usable(candidate):
                source = candidate
                break
        else:
            source = root / LALALA_ASCII_REL

    if not _lalala_dir_usable(source):
        raise FileNotFoundError(
            f"lalala 源目录不可用（缺 {LALALA_CORE_FILES}）: {source}"
        )

    for name in LALALA_CORE_FILES:
        shutil.copy2(source / name, dest / name)
    return dest


def get_lalala_dir(repo_root: Optional[Path] = None) -> str:
    root = repo_root or REPO_ROOT
    ref = root / LALALA_REFERENCE_REL

    env_val = os.environ.get("LALALA_DIR", "").strip()
    if env_val:
        return env_val

    cfg = load_v7_paths_config()
    yaml_val = str(cfg.get("lalala_dir", "") or "").strip()
    if yaml_val:
        expanded = _expand_repo(yaml_val, root)
        if _lalala_dir_usable(Path(expanded)):
            return expanded

    if _lalala_dir_usable(ref):
        return str(ref.resolve())

    for rel in DEFAULT_LALALA_CANDIDATES:
        p = root / rel
        if _lalala_dir_usable(p):
            return str(p.resolve())

    source = root / LALALA_ASCII_REL
    if not _lalala_dir_usable(source):
        source = root / LALALA_LEGACY_REL
    if _lalala_dir_usable(source):
        try:
            sync_lalala_to_reference(root)
            if _lalala_dir_usable(ref):
                return str(ref.resolve())
        except OSError:
            pass
        return str(source.resolve())

    if yaml_val:
        return _expand_repo(yaml_val, root)
    return str((root / LALALA_ASCII_REL).resolve())


def get_model_dir(repo_root: Optional[Path] = None) -> str:
    root = repo_root or REPO_ROOT
    cfg = load_v7_paths_config()
    env_val = os.environ.get("MODEL_DIR", "").strip()
    if env_val:
        return env_val
    yaml_val = str(cfg.get("model_dir", "") or "").strip()
    if yaml_val:
        return _expand_repo(yaml_val, root)
    return str(root / "models")


def get_model_file(repo_root: Optional[Path] = None) -> str:
    root = repo_root or REPO_ROOT
    cfg = load_v7_paths_config()
    name = str(cfg.get("model_file", "bc_model_ultimate_win_rate.pth") or "").strip()
    env_path = os.environ.get("V7_MODEL_PATH", "").strip()
    if env_path:
        return env_path

    model_dir = Path(get_model_dir(repo_root=root))
    direct = model_dir / name
    if direct.is_file():
        return str(direct)

    for rel in DEFAULT_MODEL_CANDIDATES:
        p = root / rel
        if p.is_file():
            return str(p)
    return str(direct)


def normalize_client_script_entry(entry: str, repo_root: Optional[Path] = None) -> str:
    """GUI/CLI 客户端字段 → 绝对路径（去掉可选的 python 前缀）。"""
    text = entry.strip().strip('"').strip("'")
    if not text:
        return ""
    if text.lower().startswith("python "):
        text = text[7:].strip()
    root = repo_root or REPO_ROOT
    path = Path(text)
    if not path.is_absolute():
        path = root / path
    return str(path.resolve())


def format_client_scripts_for_gui(
    scripts: Iterable[str | Path],
    repo_root: Optional[Path] = None,
) -> str:
    """批跑 GUI 客户端框：逗号分隔的仓库相对路径（无 python 前缀）。"""
    root = repo_root or REPO_ROOT
    parts = []
    for script in scripts:
        p = Path(script).resolve()
        try:
            parts.append(p.relative_to(root.resolve()).as_posix())
        except ValueError:
            parts.append(str(p))
    return ", ".join(parts)


def parse_server_field(value: str, repo_root: Optional[Path] = None) -> tuple[str, str]:
    """
    解析 GUI 服务器字段。
    支持仅 exe，或「exe 12」形式；返回 (exe绝对路径, argv参数字符串)。
    """
    text = value.strip().strip('"')
    if not text:
        return "", get_server_argv(repo_root)
    if text.lower().endswith(".exe"):
        parts = text.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            exe, argv = parts[0], parts[1]
        else:
            exe, argv = text, get_server_argv(repo_root)
    else:
        tokens = text.split(maxsplit=1)
        exe = tokens[0]
        argv = tokens[1] if len(tokens) > 1 else get_server_argv(repo_root)
    exe_path = Path(exe)
    if not exe_path.is_absolute():
        exe_path = (repo_root or REPO_ROOT) / exe_path
    return str(exe_path.resolve()), str(argv)


def get_v7_client_scripts(repo_root: Optional[Path] = None) -> List[str]:
    """批跑四客户端：pos0 yf1, pos1 lalala3, pos2 yf2, pos3 lalala4。"""
    root = repo_root or REPO_ROOT
    return [
        str(root / "src" / "communication" / "yf1_v7.py"),
        str(root / "src" / "communication" / "run_lalala_client3.py"),
        str(root / "src" / "communication" / "yf2_v7.py"),
        str(root / "src" / "communication" / "run_lalala_client4.py"),
    ]

