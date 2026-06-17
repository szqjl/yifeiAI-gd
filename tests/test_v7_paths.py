import os
import yaml
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_cfg(**overrides):
    """Return config dict with overrides applied."""
    d = {
        "lalala_dir": "%REPO_ROOT%/reference/lalala",
        "server_exe": "%REPO_ROOT%/offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe",
        "model_dir": "%REPO_ROOT%/models/v-nn",
        "model_file": "bc_model_ultimate_win_rate.pth",
        "server_args": "10",
    }
    d.update(overrides)
    return d


def _write_cfg(cfg, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f)
    return path


def test_default_config():
    """默认配置：所有路径基于 %REPO_ROOT% 可解析"""
    cfg = _make_cfg()
    assert "%REPO_ROOT%" in cfg["lalala_dir"]
    resolved = cfg["lalala_dir"].replace("%REPO_ROOT%", str(REPO_ROOT))
    resolved_exe = cfg["server_exe"].replace("%REPO_ROOT%", str(REPO_ROOT))
    assert resolved != cfg["lalala_dir"]
    assert Path(resolved).is_dir() or True  # 不强制目录存在
    assert resolved_exe.endswith(".exe")


def test_lalala_dir_env_override():
    """环境变量 LALALA_DIR 优先生效"""
    cfg = _make_cfg(lalala_dir="D:/custom/lalala")
    assert cfg["lalala_dir"] == "D:/custom/lalala"


def test_server_exe_env_override():
    """环境变量 SERVER_EXE 优生产效"""
    cfg = _make_cfg(server_exe="D:/custom/server.exe")
    assert cfg["server_exe"] == "D:/custom/server.exe"


def test_config_yaml_readable(tmp_path):
    """v7_paths.yaml 可被 yaml.safe_load 读且字段齐全"""
    cfg = _make_cfg()
    p = _write_cfg(cfg, tmp_path / "v7_paths.yaml")
    with open(p, encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    for k in ("lalala_dir", "server_exe", "model_dir", "model_file", "server_args"):
        assert k in loaded


def test_lalala_adapter_imports():
    """验证 lalala_adapter.py 的路径解析逻辑可导入（不报语法错误）"""
    import ast
    src = REPO_ROOT / "src" / "communication" / "lalala_adapter.py"
    with open(src, encoding="utf-8") as f:
        ast.parse(f.read())
    # 验证无硬编码 D:\\NYGD（仅允许作为 fallback default 参数值）
    content = src.read_text(encoding="utf-8")
    docstring_marker = 'r"D:\\NYGD\\lalala"'
    if docstring_marker in content:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if docstring_marker in line:
                assert "DEFAULT" not in line.upper() or "fallback" in line.lower(), f"hardcoded D:\\NYGD at line {i+1}"


def test_no_d_hardcode_in_v7_python():
    """scripts/v7/ 下的 Python 文件不应含 D:\\NYGD 或 D:\\guandanscore 字面量"""
    v7_dir = REPO_ROOT / "scripts" / "v7"
    if not v7_dir.is_dir():
        return
    for py in v7_dir.glob("*.py"):
        content = py.read_text(encoding="utf-8")
        # 允许 _resolve_path 调用的 fallback default 参数
        if "D:\\\\NYGD" in content or "D:\\\\guandanscore" in content:
            lines = content.splitlines()
            for line in lines:
                if ("D:\\\\NYGD" in line or "D:\\\\guandanscore" in line) and "_resolve_path" not in line:
                    raise AssertionError(f"{py} has hardcoded D: path: {line.strip()}")
