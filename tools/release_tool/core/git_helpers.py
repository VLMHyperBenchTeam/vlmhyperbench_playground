from __future__ import annotations

"""Вспомогательные git-утилиты (перемещены в подпакет core)."""

import contextlib
import pathlib
from typing import Iterator, Optional

from .git_utils import _run_git, GitError  # локальный импорт внутри core

__all__ = [
    "remote_branch_exists",
    "local_branch_exists",
    "fast_forward",
    "temporary_stash",
    "checkout_branch",
    "ensure_tracking",
    "calc_ahead_behind",
]

# ---------------------------------------------------------------------------
# Вспомогательные типы

class _StashResult:  # noqa: D101 – simple container
    __slots__ = ("kept",)

    def __init__(self, kept: bool = False) -> None:  # noqa: D401
        self.kept: bool = kept


# ---------------------------------------------------------------------------
# low-level helpers


def remote_branch_exists(repo: pathlib.Path, remote: str, branch: str) -> bool:
    return _run_git(repo, ["rev-parse", "--verify", f"{remote}/{branch}"], capture=True).returncode == 0


def local_branch_exists(repo: pathlib.Path, branch: str) -> bool:
    return _run_git(repo, ["show-ref", "--verify", f"refs/heads/{branch}"], capture=True).returncode == 0


def fast_forward(repo: pathlib.Path, target_ref: str) -> bool:
    proc = _run_git(repo, ["merge", "--ff-only", target_ref], capture=True)
    if proc.returncode == 0:
        return proc.stdout.strip() != ""
    if "already up to date" in (proc.stderr or proc.stdout or ""):
        return False
    raise GitError(proc.stderr or proc.stdout)


# ---------------------------------------------------------------------------
# context manager

@contextlib.contextmanager
def temporary_stash(
    repo: pathlib.Path,
    *,
    enabled: bool = True,
    include_untracked: bool = True,
    message: str = "stage0-auto-stash",
    keep: bool = False,
) -> Iterator[_StashResult]:
    result = _StashResult(False)
    if not enabled:
        yield result
        return
    push_args = [
        "stash",
        "push",
        "--include-untracked" if include_untracked else "--keep-index",
        "-m",
        message,
    ]
    _run_git(repo, push_args, capture=False)
    try:
        yield result
    finally:
        _run_git(repo, ["stash", "pop"], capture=False)
        conflicts = _run_git(repo, ["diff", "--name-only", "--diff-filter=U"], capture=True).stdout.strip()
        has_conflicts = bool(conflicts)
        if has_conflicts or keep:
            result.kept = True
        else:
            list_proc = _run_git(repo, ["stash", "list"], capture=True)
            first_line: Optional[str] = list_proc.stdout.split("\n")[0] if list_proc.stdout else None
            if first_line and message in first_line:
                ref = first_line.split(":", 1)[0]
                _run_git(repo, ["stash", "drop", ref], capture=False)
            result.kept = False


# ---------------------------------------------------------------------------
# high-level helpers

def checkout_branch(repo: pathlib.Path, branch: str, start_point: str | None = None) -> None:
    args = ["checkout", branch] if start_point is None else ["checkout", "-B", branch, start_point]
    _run_git(repo, args, capture=False)


def ensure_tracking(repo: pathlib.Path, branch: str, remote: str) -> None:
    if remote_branch_exists(repo, remote, branch):
        _run_git(repo, ["branch", "--set-upstream-to", f"{remote}/{branch}", branch], capture=False)


def calc_ahead_behind(repo: pathlib.Path, branch: str, remote_ref: str) -> tuple[int, int]:
    proc = _run_git(repo, [
        "rev-list",
        "--left-right",
        "--count",
        f"{branch}...{remote_ref}",
    ], capture=True)
    output = proc.stdout.strip()
    if proc.returncode != 0 or not output:
        return (0, 0)
    parts = output.split()
    if len(parts) == 2:
        left, right = parts
    elif len(parts) == 1:
        left, right = parts[0], "0"
    else:
        return (0, 0)
    return (int(left), int(right))