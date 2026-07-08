from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TOOL_PATH = _REPO_ROOT / "tools" / "check_remote_script_runtime.py"


def _load_tool_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_remote_script_runtime", _TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _patch_dirs(module: ModuleType, monkeypatch, tmp_path: Path) -> Path:
    remote_dir = tmp_path / "remote_script"
    remote_dir.mkdir()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "REMOTE_SCRIPT_DIR", remote_dir)
    return remote_dir


def test_passes_when_no_python_files_present(monkeypatch, tmp_path: Path) -> None:
    module = _load_tool_module()
    _patch_dirs(module, monkeypatch, tmp_path)

    exit_code, message = module.run_check()

    assert exit_code == 0
    assert "No remote_script/*.py files found" in message


def test_passes_for_valid_python_using_matching_interpreter(monkeypatch, tmp_path: Path) -> None:
    module = _load_tool_module()
    remote_dir = _patch_dirs(module, monkeypatch, tmp_path)
    (remote_dir / "ok.py").write_text("x = 1\n", encoding="utf-8")

    exit_code, message = module.run_check()

    assert exit_code == 0
    assert "OK" in message


def test_fails_for_syntax_error_using_matching_interpreter(monkeypatch, tmp_path: Path) -> None:
    module = _load_tool_module()
    remote_dir = _patch_dirs(module, monkeypatch, tmp_path)
    (remote_dir / "bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")

    exit_code, message = module.run_check()

    assert exit_code == 1
    assert "bad.py" in message


def test_falls_back_to_feature_version_static_check_when_no_interpreter_found(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_tool_module()
    remote_dir = _patch_dirs(module, monkeypatch, tmp_path)
    (remote_dir / "ok.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(module, "_find_matching_interpreter", lambda: None)

    exit_code, message = module.run_check()

    assert exit_code == 0
    assert "feature_version" in message


def test_feature_version_fallback_catches_syntax_errors(monkeypatch, tmp_path: Path) -> None:
    module = _load_tool_module()
    remote_dir = _patch_dirs(module, monkeypatch, tmp_path)
    (remote_dir / "bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(module, "_find_matching_interpreter", lambda: None)

    exit_code, message = module.run_check()

    assert exit_code == 1
    assert "bad.py" in message


def test_main_returns_run_check_exit_code(monkeypatch, tmp_path: Path) -> None:
    module = _load_tool_module()
    _patch_dirs(module, monkeypatch, tmp_path)

    assert module.main([]) == 0


def test_current_remote_script_tree_passes(capsys) -> None:
    module = _load_tool_module()

    exit_code, message = module.run_check()

    assert exit_code == 0, message
