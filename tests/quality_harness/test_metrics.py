from __future__ import annotations

from pathlib import Path

from ableton_cli.quality_harness.metrics import analyze_python_files, compute_god_class_risk


def test_analyze_python_files_computes_function_and_class_metrics(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        "\n".join(
            [
                "import math",
                "",
                "def foo(a, b, c, d, e, f):",
                "    if a and b:",
                "        for i in range(3):",
                "            if i % 2:",
                "                return i",
                "    return 0",
                "",
                "class Big:",
                "    def first(self, x, y, z):",
                "        if x:",
                "            return y",
                "        return z",
                "",
                "    def second(self, p, q, r, s, t, u, v, w):",
                "        for i in range(2):",
                "            if i:",
                "                if q:",
                "                    return i",
                "        return 0",
                "",
                "    def _hidden(self):",
                "        return 1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = analyze_python_files([source], root_dir=tmp_path)

    foo = next(item for item in result.function_metrics if item.qualname == "foo")
    big = next(item for item in result.class_metrics if item.qualname == "Big")

    assert foo.complexity == 5
    assert foo.nesting == 3
    assert foo.args == 6
    assert foo.imports == 0
    assert foo.estimated_tokens > 0

    assert big.method_count == 3
    assert big.public_method_count == 2
    assert big.args == 8
    assert big.complexity == 7
    assert big.estimated_tokens > 0
    assert big.god_class_risk == compute_god_class_risk(
        method_count=3,
        public_method_count=2,
        complexity=7,
        estimated_tokens=big.estimated_tokens,
        args=8,
    )

    file_metric = result.file_metrics[0]
    assert file_metric.path == "sample.py"
    assert file_metric.imports == 1
    assert file_metric.complexity >= foo.complexity


def test_analyze_python_files_continues_when_parse_error_exists(tmp_path: Path) -> None:
    good = tmp_path / "good.py"
    good.write_text("def ok():\n    return 1\n", encoding="utf-8")

    bad = tmp_path / "bad.py"
    bad.write_text("def broken(:\n    return 2\n", encoding="utf-8")

    result = analyze_python_files([good, bad], root_dir=tmp_path)

    assert len(result.parse_errors) == 1
    assert result.parse_errors[0].path == "bad.py"
    assert [metric.path for metric in result.file_metrics] == ["good.py"]
