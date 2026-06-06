# -*- coding: utf-8 -*-

import os
from pathlib import Path

import pytest

from src.utils import v7_paths


def test_get_server_exe_prefers_existing_candidate(tmp_path, monkeypatch):
    exe = tmp_path / "guandan_offline_v1006" / "windows" / "guandan_offline_v1006.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"stub")
    monkeypatch.setenv("SERVER_EXE", "")
    monkeypatch.setattr(v7_paths, "V7_PATHS_FILE", tmp_path / "missing.yaml")
    assert v7_paths.get_server_exe(repo_root=tmp_path) == str(exe)


def test_get_lalala_dir_missing_returns_yaml_or_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("LALALA_DIR", "")
    cfg = tmp_path / "config" / "v7_paths.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('lalala_dir: "%REPO_ROOT%/reference/lalala"\n', encoding="utf-8")
    monkeypatch.setattr(v7_paths, "V7_PATHS_FILE", cfg)
    v7_paths.load_v7_paths_config.cache_clear()
    assert v7_paths.get_lalala_dir(repo_root=tmp_path).endswith(
        os.path.join("reference", "lalala")
    )


def test_get_model_file_env_override(tmp_path, monkeypatch):
    model = tmp_path / "custom.pth"
    model.write_bytes(b"x")
    monkeypatch.setenv("V7_MODEL_PATH", str(model))
    assert v7_paths.get_model_file(repo_root=tmp_path) == str(model)


def test_normalize_client_script_entry_strips_python_prefix(tmp_path, monkeypatch):
    script = tmp_path / "src" / "communication" / "yf1_v7.py"
    script.parent.mkdir(parents=True)
    script.write_text("# stub", encoding="utf-8")
    monkeypatch.setattr(v7_paths, "REPO_ROOT", tmp_path)
    got = v7_paths.normalize_client_script_entry(
        f"python src/communication/yf1_v7.py", repo_root=tmp_path
    )
    assert got == str(script.resolve())


def test_get_server_exe_fallback_when_offline_platform_missing(tmp_path, monkeypatch):
    """yaml 指向 offline_platform 不存在时，回退仓库根 guandan_offline_v1006。"""
    legacy = (
        tmp_path
        / "guandan_offline_v1006"
        / "windows"
        / "guandan_offline_v1006.exe"
    )
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"stub")
    cfg = tmp_path / "config" / "v7_paths.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        'server_exe: "%REPO_ROOT%/offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("SERVER_EXE", "")
    monkeypatch.setattr(v7_paths, "V7_PATHS_FILE", cfg)
    v7_paths.load_v7_paths_config.cache_clear()
    assert v7_paths.get_server_exe(repo_root=tmp_path) == str(legacy)


def test_parse_server_field_splits_exe_and_argv(tmp_path, monkeypatch):
    exe = tmp_path / "guandan_offline_v1006.exe"
    exe.write_bytes(b"stub")
    monkeypatch.setattr(v7_paths, "REPO_ROOT", tmp_path)
    path, argv = v7_paths.parse_server_field(f"{exe} 12", repo_root=tmp_path)
    assert path == str(exe.resolve())
    assert argv == "12"
