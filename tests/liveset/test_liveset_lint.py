from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from live_set_builder import SampleSpec, SetSpec, TrackSpec, build_live_set_xml, write_live_set

from ableton_cli.errors import AppError, ErrorCode, ExitCode
from ableton_cli.liveset.document import load_live_set
from ableton_cli.liveset.lint import lint_live_set, require_no_errors
from ableton_cli.liveset.media import find_project_root, scan_media

PROJECT_INFO = "Ableton Project Info"


def _project(tmp_path: Path, samples: list[SampleSpec], *, subdir: str = "") -> Path:
    project = tmp_path / "Song Project"
    (project / PROJECT_INFO).mkdir(parents=True)
    spec = SetSpec(tracks=[TrackSpec(tag="AudioTrack", samples=samples)])
    return write_live_set(project / subdir / "Song.als", build_live_set_xml(spec))


def _audio_set(samples: list[SampleSpec]) -> SetSpec:
    return SetSpec(tracks=[TrackSpec(tag="AudioTrack", samples=samples)])


def _codes(findings) -> list[str]:
    return [finding.code for finding in findings]


def test_find_project_root_walks_up_to_project_info(tmp_path: Path) -> None:
    set_path = _project(tmp_path, [], subdir="Backup")

    assert find_project_root(set_path) == tmp_path / "Song Project"


def test_find_project_root_returns_none_outside_a_project(tmp_path: Path) -> None:
    assert find_project_root(tmp_path / "Loose.als") is None


def test_project_relative_sample_present_has_no_findings(tmp_path: Path) -> None:
    set_path = _project(tmp_path, [SampleSpec(relative_path="Samples/kick.wav")])
    (set_path.parent / "Samples").mkdir()
    (set_path.parent / "Samples" / "kick.wav").write_bytes(b"RIFF")

    assert scan_media(load_live_set(set_path)).findings == []


def test_project_relative_sample_resolves_from_backup_subfolder(tmp_path: Path) -> None:
    set_path = _project(tmp_path, [SampleSpec(relative_path="Samples/kick.wav")], subdir="Backup")
    samples = tmp_path / "Song Project" / "Samples"
    samples.mkdir()
    (samples / "kick.wav").write_bytes(b"RIFF")

    assert scan_media(load_live_set(set_path)).findings == []


def test_missing_project_samples_are_reported_once_without_absolute_paths(
    tmp_path: Path,
) -> None:
    samples = [
        SampleSpec(relative_path="Samples/kick.wav", path=str(tmp_path / "abs" / "kick.wav")),
        SampleSpec(relative_path="Samples/kick.wav"),
        SampleSpec(relative_path="Samples/Recorded/vox.wav"),
    ]

    findings = scan_media(load_live_set(_project(tmp_path, samples))).findings

    assert _codes(findings) == ["media_missing"]
    assert findings[0].severity == "warning"
    assert findings[0].details == {
        "count": 2,
        "files": [
            {"relative_path": "Samples/Recorded/vox.wav", "file_name": "vox.wav"},
            {"relative_path": "Samples/kick.wav", "file_name": "kick.wav"},
        ],
    }
    assert str(tmp_path) not in repr(findings[0].details)


def test_project_sample_ignores_stored_absolute_path(tmp_path: Path) -> None:
    # Live resolves project-relative samples against the project folder only; an
    # existing file at the stored absolute Path does not make the sample present.
    stale = tmp_path / "old" / "kick.wav"
    stale.parent.mkdir()
    stale.write_bytes(b"RIFF")
    samples = [SampleSpec(relative_path="Samples/kick.wav", path=str(stale))]

    findings = scan_media(load_live_set(_project(tmp_path, samples))).findings

    assert _codes(findings) == ["media_missing"]


def test_non_project_samples_are_counted_as_unchecked(tmp_path: Path) -> None:
    # Library-relative (5, 6, 7) and other references resolve against locations this
    # tool must not assume, so they are counted, never reported missing or present.
    samples = [
        SampleSpec(
            relative_path="Samples/Kick.aif",
            path="/build/Core Library/Kick.aif",
            relative_path_type=5,
        ),
        SampleSpec(relative_path="Samples/IR.wav", path="/nowhere/IR.wav", relative_path_type=7),
        SampleSpec(relative_path="Samples/IR.wav", path="/nowhere/IR.wav", relative_path_type=7),
        SampleSpec(relative_path="../x.wav", path="/nowhere/x.wav", relative_path_type=1),
    ]

    scan = scan_media(load_live_set(_project(tmp_path, samples)))

    assert scan.findings == []
    assert scan.summary == {
        "checked_count": 0,
        "unchecked_count": 3,
        "unchecked_by_relative_path_type": {"1": 1, "5": 1, "7": 1},
    }


def test_only_sample_references_are_scanned(tmp_path: Path) -> None:
    def _preset_ref(root: ET.Element) -> None:
        ref = ET.SubElement(ET.SubElement(root.find("LiveSet"), "BranchSourceContext"), "FileRef")
        ET.SubElement(ref, "RelativePathType", Value="3")
        ET.SubElement(ref, "RelativePath", Value="Presets/Missing.adg")

    project = tmp_path / "Song Project"
    (project / PROJECT_INFO).mkdir(parents=True)
    root = build_live_set_xml(SetSpec())
    _preset_ref(root)

    scan = scan_media(load_live_set(write_live_set(project / "Song.als", root)))

    assert scan.findings == []
    assert scan.summary["checked_count"] == 0


def test_project_relative_samples_outside_a_project_are_unresolvable(live_set_factory) -> None:
    spec = _audio_set([SampleSpec(relative_path="Samples/a.wav")])

    findings = scan_media(load_live_set(live_set_factory(spec))).findings

    assert _codes(findings) == ["project_root_not_found"]
    assert findings[0].details == {
        "count": 1,
        "files": [{"relative_path": "Samples/a.wav", "file_name": "a.wav"}],
    }


def test_empty_file_refs_are_ignored(tmp_path: Path) -> None:
    samples = [SampleSpec(relative_path="", path="", relative_path_type=0)]

    assert scan_media(load_live_set(_project(tmp_path, samples))).findings == []


def test_lint_report_counts_findings_by_severity(live_set_factory) -> None:
    spec = _audio_set([SampleSpec(relative_path="Samples/a.wav")])
    spec.next_pointee_id = 1

    report = lint_live_set(load_live_set(live_set_factory(spec)))

    assert report["error_count"] == 1
    assert report["warning_count"] == 1
    assert [finding["code"] for finding in report["findings"]] == [
        "next_pointee_id_too_low",
        "project_root_not_found",
    ]
    assert report["version"]["minor"] == "12.0_12402"
    assert report["path"].endswith("Test.als")
    assert report["media"] == {
        "checked_count": 1,
        "unchecked_count": 0,
        "unchecked_by_relative_path_type": {},
    }


def test_require_no_errors_passes_warning_only_reports(live_set_factory) -> None:
    spec = _audio_set([SampleSpec(relative_path="Samples/a.wav")])
    report = lint_live_set(load_live_set(live_set_factory(spec)))

    assert require_no_errors(report) is report


def test_require_no_errors_fails_with_integrity_error(live_set_factory) -> None:
    def _dangle(root: ET.Element) -> None:
        ET.SubElement(root.find("LiveSet"), "PointeeId", Value="424242")

    report = lint_live_set(load_live_set(live_set_factory(mutate=_dangle)))

    with pytest.raises(AppError) as exc:
        require_no_errors(report)

    assert exc.value.error_code == ErrorCode.SET_INTEGRITY_FAILED
    assert exc.value.exit_code == ExitCode.EXECUTION_FAILED
    assert exc.value.details["findings"] == report["findings"]
