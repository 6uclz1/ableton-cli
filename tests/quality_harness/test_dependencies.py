from __future__ import annotations

from pathlib import Path

from ableton_cli.quality_harness.dependencies import analyze_dependencies
from ableton_cli.quality_harness.models import LayerRule


def test_analyze_dependencies_detects_import_cycle(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a\n", encoding="utf-8")

    result = analyze_dependencies(
        paths=[tmp_path / "a.py", tmp_path / "b.py"],
        root_dir=tmp_path,
        layers=[],
    )

    assert len(result.cycles) == 1
    assert set(result.cycles[0].modules) == {"a", "b"}


def test_analyze_dependencies_detects_layer_violation(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "high").mkdir(parents=True)
    (src / "low").mkdir(parents=True)

    (src / "high" / "api.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (src / "low" / "impl.py").write_text("from high import api\n", encoding="utf-8")

    result = analyze_dependencies(
        paths=[src / "high" / "api.py", src / "low" / "impl.py"],
        root_dir=tmp_path,
        layers=[
            LayerRule(name="high", include=["src/high/**/*.py"]),
            LayerRule(name="low", include=["src/low/**/*.py"]),
        ],
    )

    assert len(result.layer_violations) == 1
    violation = result.layer_violations[0]
    assert violation.from_layer == "low"
    assert violation.to_layer == "high"
