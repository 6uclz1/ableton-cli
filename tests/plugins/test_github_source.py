from __future__ import annotations

import subprocess

import pytest

from ableton_cli.errors import AppError
from ableton_cli.plugins.github import GitHubSource, parse_github_url, pin_source, resolve_ref

SOURCE = GitHubSource(owner="someone", repo="ableton-cli-demo")
SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40


@pytest.mark.parametrize(
    ("url", "ref"),
    [
        ("https://github.com/someone/ableton-cli-demo", None),
        ("https://github.com/someone/ableton-cli-demo/", None),
        ("https://github.com/someone/ableton-cli-demo.git", None),
        ("https://GitHub.com/someone/ableton-cli-demo/tree/v1.2.0", "v1.2.0"),
        ("https://github.com/someone/ableton-cli-demo/tree/feature/gate", "feature/gate"),
    ],
)
def test_parse_github_url_accepts_repository_urls(url: str, ref: str | None) -> None:
    assert parse_github_url(url) == (SOURCE, ref)


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/someone/repo",
        "https://gitlab.com/someone/repo",
        "https://github.com.evil.example/someone/repo",
        "https://user@github.com/someone/repo",
        "https://github.com:8443/someone/repo",
        "https://github.com/someone",
        "https://github.com/someone/repo/blob/main/README.md",
        "https://github.com/someone/repo/tree/",
        "https://github.com/someone/repo?tab=readme",
        "https://github.com/someone/repo/tree/--upload-pack=evil",
        "https://github.com/someone/repo/tree/a..b",
        "git@github.com:someone/repo.git",
    ],
)
def test_parse_github_url_rejects_everything_else(url: str) -> None:
    with pytest.raises(AppError) as exc_info:
        parse_github_url(url)

    assert exc_info.value.error_code == "INVALID_ARGUMENT"


def _ls_remote(stdout: str, calls: list[list[str]] | None = None):
    def run(argv):
        if calls is not None:
            calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, stdout=stdout, stderr="")

    return run


def test_resolve_ref_uses_the_default_branch_when_no_ref_is_given() -> None:
    calls: list[list[str]] = []

    rev = resolve_ref(SOURCE, None, run=_ls_remote(f"{SHA_A}\tHEAD\n", calls))

    assert rev == SHA_A
    assert calls == [["git", "ls-remote", SOURCE.url, "HEAD"]]


def test_resolve_ref_prefers_the_peeled_commit_of_an_annotated_tag() -> None:
    stdout = f"{SHA_A}\trefs/tags/v1\n{SHA_B}\trefs/tags/v1^{{}}\n"

    assert resolve_ref(SOURCE, "v1", run=_ls_remote(stdout)) == SHA_B


def test_resolve_ref_resolves_branches() -> None:
    assert resolve_ref(SOURCE, "main", run=_ls_remote(f"{SHA_C}\trefs/heads/main\n")) == SHA_C


def test_resolve_ref_refuses_a_name_that_is_both_branch_and_tag() -> None:
    stdout = f"{SHA_A}\trefs/heads/v1\n{SHA_B}\trefs/tags/v1\n"

    with pytest.raises(AppError) as exc_info:
        resolve_ref(SOURCE, "v1", run=_ls_remote(stdout))

    assert exc_info.value.error_code == "INVALID_ARGUMENT"


def test_resolve_ref_fails_for_unknown_refs() -> None:
    with pytest.raises(AppError) as exc_info:
        resolve_ref(SOURCE, "nope", run=_ls_remote(""))

    assert exc_info.value.error_code == "INVALID_ARGUMENT"


def test_resolve_ref_passes_full_shas_through_without_network() -> None:
    def run(argv):
        raise AssertionError("git must not run for a full SHA")

    assert resolve_ref(SOURCE, SHA_A, run=run) == SHA_A


def test_missing_git_is_config_invalid() -> None:
    def run(argv):
        raise FileNotFoundError(argv[0])

    with pytest.raises(AppError) as exc_info:
        resolve_ref(SOURCE, "main", run=run)

    assert exc_info.value.error_code == "CONFIG_INVALID"


def test_failing_git_is_plugin_install_failed_with_stderr() -> None:
    def run(argv):
        return subprocess.CompletedProcess(
            list(argv), 128, stdout="", stderr="repository not found"
        )

    with pytest.raises(AppError) as exc_info:
        resolve_ref(SOURCE, "main", run=run)

    assert exc_info.value.error_code == "PLUGIN_INSTALL_FAILED"
    assert exc_info.value.details["stderr"] == "repository not found"


def test_pin_source_refuses_conflicting_url_and_option_refs() -> None:
    with pytest.raises(AppError) as exc_info:
        pin_source(f"{SOURCE.url}/tree/v1", "v2", run=_ls_remote(""))

    assert exc_info.value.error_code == "INVALID_ARGUMENT"


def test_pin_source_records_the_requested_ref_and_commit() -> None:
    pinned = pin_source(SOURCE.url, "main", run=_ls_remote(f"{SHA_C}\trefs/heads/main\n"))

    assert (pinned.source, pinned.requested_ref, pinned.rev) == (SOURCE, "main", SHA_C)
    assert pinned.source.requirement(pinned.rev) == f"git+{SOURCE.url}@{SHA_C}"


def test_source_matches_urls_however_they_are_spelled() -> None:
    assert SOURCE.matches_url("https://github.com/Someone/ableton-cli-demo.git/")
    assert not SOURCE.matches_url("https://github.com/someone/ableton-cli-demo2")
