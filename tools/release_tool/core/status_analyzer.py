from __future__ import annotations

"""Утилиты для анализа git-репозитория (перемещены в core)."""

import pathlib
from dataclasses import dataclass

from .git_helpers import remote_branch_exists, calc_ahead_behind
from .git_utils import has_uncommitted_changes

__all__ = ["RepoStatus", "analyze_repo_status"]


@dataclass(slots=True)
class RepoStatus:
    ahead: int
    behind: int
    uncommitted: bool


def analyze_repo_status(repo: pathlib.Path, branch: str, remote: str = "origin") -> RepoStatus:
    if remote_branch_exists(repo, remote, branch):
        ahead, behind = calc_ahead_behind(repo, branch, f"{remote}/{branch}")
    else:
        ahead = behind = 0
    uncommitted = has_uncommitted_changes(repo)
    return RepoStatus(ahead=ahead, behind=behind, uncommitted=uncommitted)