"""GitHub plugin sources: parse the URL a user typed and pin a ref to a commit."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from ..errors import AppError, ErrorCode, ExitCode

CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_REF_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{1,255}$")
_STDERR_TAIL = 2000


@dataclass(frozen=True, slots=True)
class GitHubSource:
    owner: str
    repo: str

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"

    def requirement(self, rev: str) -> str:
        return f"git+{self.url}@{rev}"

    def matches_url(self, url: str) -> bool:
        """True for the same repository however the URL is spelled (case, ``.git``, slash)."""
        return _normalize(url) == _normalize(self.url)


@dataclass(frozen=True, slots=True)
class PinnedSource:
    source: GitHubSource
    requested_ref: str | None
    rev: str


def parse_github_url(url: str) -> tuple[GitHubSource, str | None]:
    """``https://github.com/<owner>/<repo>[.git][/tree/<ref>]`` -> (source, ref or None)."""
    segments = _github_path_segments(url)
    if len(segments) < 2:
        raise _invalid_url(url)
    owner, repo = segments[0], segments[1].removesuffix(".git")
    if (
        _OWNER_PATTERN.fullmatch(owner) is None
        or _REPO_PATTERN.fullmatch(repo) is None
        or repo in (".", "..")
    ):
        raise _invalid_url(url)
    rest = segments[2:]
    if not rest:
        return GitHubSource(owner=owner, repo=repo), None
    if rest[0] != "tree" or len(rest) < 2:
        raise _invalid_url(url)
    return GitHubSource(owner=owner, repo=repo), _validated_ref("/".join(rest[1:]))


def _github_path_segments(url: str) -> list[str]:
    """The path segments of a plain ``https://github.com/...`` URL; anything else is refused."""
    parts = urlsplit(url.strip())
    shape = (parts.scheme, (parts.hostname or "").lower(), parts.port, parts.username)
    if shape != ("https", "github.com", None, None) or parts.query or parts.fragment:
        raise _invalid_url(url)
    return [segment for segment in parts.path.split("/") if segment]


def pin_source(url: str, ref: str | None, *, run: CommandRunner) -> PinnedSource:
    """Parse ``url`` and resolve the requested ref to the commit to install."""
    source, url_ref = parse_github_url(url)
    option_ref = None if ref is None else _validated_ref(ref)
    if url_ref is not None and option_ref is not None and url_ref != option_ref:
        raise AppError(
            error_code=ErrorCode.INVALID_ARGUMENT,
            message=f"The URL names ref {url_ref!r} but --ref is {option_ref!r}",
            hint="Give the ref in the URL or with --ref, not both.",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )
    requested = url_ref if url_ref is not None else option_ref
    return PinnedSource(
        source=source,
        requested_ref=requested,
        rev=resolve_ref(source, requested, run=run),
    )


def resolve_ref(source: GitHubSource, ref: str | None, *, run: CommandRunner) -> str:
    """Branch, tag or SHA -> full commit SHA. ``None`` means the default branch."""
    if ref is not None and SHA_PATTERN.fullmatch(ref):
        return ref
    wanted = "HEAD" if ref is None else ref
    completed = run_tool(run, ["git", "ls-remote", source.url, wanted], what="git ls-remote")
    advertised: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        sha, _, name = line.partition("\t")
        if SHA_PATTERN.fullmatch(sha) and name:
            advertised[name] = sha
    for candidate in _ref_candidates(source, wanted, advertised):
        if candidate in advertised:
            return advertised[candidate]
    raise AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=f"Ref {wanted!r} was not found in {source.url}",
        hint="Check the branch or tag name, or pass a full commit SHA with --ref.",
        exit_code=ExitCode.INVALID_ARGUMENT,
    )


def _ref_candidates(source: GitHubSource, wanted: str, advertised: dict[str, str]) -> list[str]:
    """Advertised ref names that ``wanted`` may mean, best first (peeled tags before tags)."""
    if wanted == "HEAD" or wanted.startswith("refs/"):
        return [f"{wanted}^{{}}", wanted]
    branch, tag = f"refs/heads/{wanted}", f"refs/tags/{wanted}"
    if branch in advertised and tag in advertised:
        raise AppError(
            error_code=ErrorCode.INVALID_ARGUMENT,
            message=f"{wanted!r} is both a branch and a tag in {source.url}",
            hint=f"Pass refs/heads/{wanted} or refs/tags/{wanted}.",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )
    return [branch, f"{tag}^{{}}", tag]


def run_subprocess(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    # A credential prompt would hang a non-interactive CLI; fail instead.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(list(argv), capture_output=True, text=True, check=False, env=env)


def run_tool(
    run: CommandRunner, argv: Sequence[str], *, what: str
) -> subprocess.CompletedProcess[str]:
    try:
        completed = run(argv)
    except FileNotFoundError as exc:
        raise AppError(
            error_code=ErrorCode.CONFIG_INVALID,
            message=f"'{argv[0]}' was not found on PATH",
            hint=f"Install {argv[0]} and make sure it is on PATH; plugin installs need git and uv.",
            exit_code=ExitCode.CONFIG_INVALID,
        ) from exc
    if completed.returncode != 0:
        raise AppError(
            error_code=ErrorCode.PLUGIN_INSTALL_FAILED,
            message=f"{what} failed with exit code {completed.returncode}",
            hint="Read details.stderr; check the URL, ref and network access.",
            exit_code=ExitCode.EXECUTION_FAILED,
            details={"tool": what, "stderr": completed.stderr.strip()[-_STDERR_TAIL:]},
        )
    return completed


def _validated_ref(ref: str) -> str:
    if _REF_PATTERN.fullmatch(ref) is None or ref.startswith(("-", "/")) or ".." in ref:
        raise AppError(
            error_code=ErrorCode.INVALID_ARGUMENT,
            message=f"Invalid ref: {ref!r}",
            hint="Use a branch name, tag name or full commit SHA.",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )
    return ref


def _normalize(url: str) -> str:
    return url.strip().rstrip("/").removesuffix(".git").lower()


def _invalid_url(url: str) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=f"Not a GitHub repository URL: {url!r}",
        hint="Use https://github.com/<owner>/<repo>, optionally ending in /tree/<ref>.",
        exit_code=ExitCode.INVALID_ARGUMENT,
    )
