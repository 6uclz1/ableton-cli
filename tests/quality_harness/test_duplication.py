from __future__ import annotations

from pathlib import Path

from ableton_cli.quality_harness.duplication import detect_duplicate_groups
from ableton_cli.quality_harness.metrics import analyze_python_files


def test_detect_duplicate_groups_for_normalized_functions(tmp_path: Path) -> None:
    source = tmp_path / "dups.py"
    source.write_text(
        "\n".join(
            [
                "def one(values, threshold):",
                "    total = 0",
                "    for item in values:",
                "        if item > threshold:",
                "            total += item",
                "    return total",
                "",
                "def two(items, limit):",
                "    result = 0",
                "    for value in items:",
                "        if value > limit:",
                "            result += value",
                "    return result",
                "",
            ]
        ),
        encoding="utf-8",
    )

    analysis = analyze_python_files([source], root_dir=tmp_path)
    groups = detect_duplicate_groups(
        analysis.duplication_candidates,
        min_lines=4,
        min_tokens=10,
    )

    assert len(groups) == 1
    assert groups[0].occurrences == 2
    assert {item.qualname for item in groups[0].locations} == {"one", "two"}


def test_detect_duplicate_groups_respects_minimum_size_filters(tmp_path: Path) -> None:
    source = tmp_path / "dups.py"
    source.write_text(
        "\n".join(
            [
                "def one(values, threshold):",
                "    total = 0",
                "    for item in values:",
                "        if item > threshold:",
                "            total += item",
                "    return total",
                "",
                "def two(items, limit):",
                "    result = 0",
                "    for value in items:",
                "        if value > limit:",
                "            result += value",
                "    return result",
                "",
            ]
        ),
        encoding="utf-8",
    )

    analysis = analyze_python_files([source], root_dir=tmp_path)
    groups = detect_duplicate_groups(
        analysis.duplication_candidates,
        min_lines=20,
        min_tokens=200,
    )

    assert groups == []
