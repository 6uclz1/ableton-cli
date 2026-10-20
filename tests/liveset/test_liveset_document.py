from __future__ import annotations

import gzip
from pathlib import Path

import pytest
from live_set_builder import SetSpec

from ableton_cli.errors import AppError, ErrorCode, ExitCode
from ableton_cli.liveset.document import load_live_set


def _assert_error(
    exc: pytest.ExceptionInfo[AppError], code: ErrorCode, exit_code: ExitCode
) -> None:
    assert exc.value.error_code == code
    assert exc.value.exit_code == exit_code
    assert exc.value.hint


def test_load_live_set_reads_root_and_version(live_set_factory) -> None:
    path = live_set_factory(SetSpec(creator="Ableton Live 12.4.6"))

    document = load_live_set(path)

    assert document.path == path
    assert document.live_set.tag == "LiveSet"
    assert document.version.major == "5"
    assert document.version.minor == "12.0_12402"
    assert document.version.creator == "Ableton Live 12.4.6"


def test_load_live_set_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AppError) as exc:
        load_live_set(tmp_path / "missing.als")

    _assert_error(exc, ErrorCode.INVALID_ARGUMENT, ExitCode.INVALID_ARGUMENT)


def test_load_live_set_rejects_directory(tmp_path: Path) -> None:
    with pytest.raises(AppError) as exc:
        load_live_set(tmp_path)

    _assert_error(exc, ErrorCode.INVALID_ARGUMENT, ExitCode.INVALID_ARGUMENT)


def test_load_live_set_rejects_non_gzip(tmp_path: Path) -> None:
    path = tmp_path / "plain.als"
    path.write_text("<Ableton />", encoding="utf-8")

    with pytest.raises(AppError) as exc:
        load_live_set(path)

    _assert_error(exc, ErrorCode.SET_FILE_INVALID, ExitCode.INVALID_ARGUMENT)


def test_load_live_set_rejects_truncated_gzip(live_set_factory) -> None:
    path = live_set_factory()
    path.write_bytes(path.read_bytes()[:40])

    with pytest.raises(AppError) as exc:
        load_live_set(path)

    _assert_error(exc, ErrorCode.SET_FILE_INVALID, ExitCode.INVALID_ARGUMENT)


def test_load_live_set_rejects_malformed_xml(tmp_path: Path) -> None:
    path = tmp_path / "broken.als"
    path.write_bytes(gzip.compress(b"<Ableton><LiveSet>"))

    with pytest.raises(AppError) as exc:
        load_live_set(path)

    _assert_error(exc, ErrorCode.SET_FILE_INVALID, ExitCode.INVALID_ARGUMENT)


@pytest.mark.parametrize(
    "payload",
    [b"<NotAbleton><LiveSet /></NotAbleton>", b"<Ableton MajorVersion='5' />"],
)
def test_load_live_set_rejects_wrong_document_shape(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "shape.als"
    path.write_bytes(gzip.compress(payload))

    with pytest.raises(AppError) as exc:
        load_live_set(path)

    _assert_error(exc, ErrorCode.SET_FILE_INVALID, ExitCode.INVALID_ARGUMENT)


@pytest.mark.parametrize(
    ("major", "minor"),
    [("5", "11.0_11300"), ("4", "12.0_12402"), ("5", "13.0_1"), ("5", "")],
)
def test_load_live_set_rejects_unsupported_versions(
    live_set_factory, major: str, minor: str
) -> None:
    path = live_set_factory(SetSpec(major_version=major, minor_version=minor))

    with pytest.raises(AppError) as exc:
        load_live_set(path)

    _assert_error(exc, ErrorCode.SET_SCHEMA_UNSUPPORTED, ExitCode.INVALID_ARGUMENT)
    assert exc.value.details["minor_version"] == minor
