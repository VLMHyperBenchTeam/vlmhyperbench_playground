from __future__ import annotations

"""Утилиты для работы с `git` через subprocess` (перемещено в подпакет core)."""

import pathlib
import subprocess
from typing import List, Optional

__all__ = [
    "GitError",
    "_run_git",
    "has_changes_since_last_tag",
    "get_last_tag",
    "get_log_since_tag",
    "commit_and_tag",
    "get_uncommitted_changes",
    "has_uncommitted_changes",
    "commit_all",
    "get_diff_stat",
    "get_full_diff",
    "get_diff_since_tag",
    "has_commits_to_push",
]


class GitError(RuntimeError):
    """Исключение git-операций."""


def _run_git(path: pathlib.Path, args: List[str], capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Выполнить git-команду в каталоге *path*."""
    kwargs = {
        "text": True,
        "encoding": "utf-8",
        "check": False,
        "cwd": str(path),
    }
    if capture:
        kwargs |= {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    return subprocess.run(["git", *args], **kwargs)  # type: ignore[arg-type,call-overload]


# --- helpers ----------------------------------------------------------

def has_changes_since_last_tag(repo_path: pathlib.Path) -> bool:
    last_tag = get_last_tag(repo_path)
    if last_tag is None:
        return True
    proc = _run_git(repo_path, ["rev-list", f"{last_tag}..HEAD", "--count"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return int(proc.stdout.strip() or "0") > 0


def get_last_tag(repo_path: pathlib.Path) -> Optional[str]:
    proc = _run_git(repo_path, ["describe", "--tags", "--abbrev=0"])
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def get_log_since_tag(repo_path: pathlib.Path, tag: Optional[str]) -> str:
    revspec = f"{tag}..HEAD" if tag else "HEAD"
    fmt = "%s%n%b%x00"
    proc = _run_git(repo_path, ["log", revspec, f"--pretty=format:{fmt}"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    raw_output = proc.stdout
    if not raw_output:
        return ""
    commits_raw = raw_output.split("\x00")
    commits = [c.strip() for c in commits_raw if c.strip()]
    formatted: list[str] = []
    for idx, commit_msg in enumerate(commits, 1):
        formatted.append(f"коммит {idx}\n{commit_msg.strip()}\n")
    return "\n".join(formatted).strip()


def commit_and_tag(
    repo_path: pathlib.Path,
    commit_message: str,
    tag_name: str,
    remote: str = "origin",
    push: bool = False,
    dry_run: bool = False,
) -> None:
    if dry_run:
        print(f"[dry-run] git -C {repo_path} commit -m \"{commit_message}\"")
        print(f"[dry-run] git -C {repo_path} tag -a {tag_name} -m \"{commit_message}\"")
        if push:
            print(f"[dry-run] git -C {repo_path} push {remote}")
            print(f"[dry-run] git -C {repo_path} push {remote} {tag_name}")
        return
    for cmd in [["commit", "-m", commit_message], ["tag", "-a", tag_name, "-m", commit_message]]:
        proc = _run_git(repo_path, cmd, capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr or f"git {' '.join(cmd)} failed in {repo_path}")
    if push:
        for cmd in [["push", remote], ["push", remote, tag_name]]:
            proc = _run_git(repo_path, cmd, capture=False)
            if proc.returncode != 0:
                raise GitError(proc.stderr or f"git {' '.join(cmd)} failed in {repo_path}")


def get_uncommitted_changes(repo_path: pathlib.Path) -> str:
    proc = _run_git(repo_path, ["status", "--porcelain"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def has_uncommitted_changes(repo_path: pathlib.Path) -> bool:
    return bool(get_uncommitted_changes(repo_path))


def _get_current_branch(repo_path: pathlib.Path) -> str:
    proc = _run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def commit_all(repo_path: pathlib.Path, commit_message: str, remote: str = "origin", push: bool = False, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] git -C {repo_path} add -A")
        print(f"[dry-run] git -C {repo_path} commit -m \"{commit_message}\"")
        if push:
            print(f"[dry-run] git -C {repo_path} push {remote}")
        return
    proc = _run_git(repo_path, ["add", "-A"], capture=False)
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    proc = _run_git(repo_path, ["commit", "-m", commit_message], capture=True)
    if proc.returncode != 0:
        combined_output = (proc.stdout or "") + (proc.stderr or "")
        if "nothing to commit" in combined_output or "nothing added to commit" in combined_output:
            print(f"[git_utils] {repo_path.name}: нет изменений для коммита (пропускаем commit)")
        else:
            raise GitError(proc.stderr or proc.stdout)
    if push:
        _push_repo(repo_path, remote)


def get_diff_stat(repo_path: pathlib.Path) -> str:
    proc = _run_git(repo_path, ["diff", "--stat"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def get_full_diff(repo_path: pathlib.Path) -> str:
    proc = _run_git(repo_path, ["diff"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def get_diff_since_tag(repo_path: pathlib.Path, tag: Optional[str]) -> str:
    revspec = f"{tag}..HEAD" if tag else "HEAD^..HEAD"
    proc = _run_git(repo_path, ["diff", revspec])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def _push_repo(repo_path: pathlib.Path, remote: str = "origin") -> None:
    proc = _run_git(repo_path, ["push", remote], capture=True)
    if proc.returncode == 0:
        return
    stderr = proc.stderr or ""
    phrases = ["set upstream", "--set-upstream", "have no upstream", "upstream branch"]
    if any(p in stderr for p in phrases):
        branch = _get_current_branch(repo_path)
        fallback_cmd = ["push", "--set-upstream", remote, branch]
        print(f"[git_utils] upstream not set, выполняем: git {' '.join(fallback_cmd)}")
        fallback_proc = _run_git(repo_path, fallback_cmd, capture=True)
        if fallback_proc.returncode != 0:
            raise GitError(fallback_proc.stderr or stderr)
    else:
        raise GitError(stderr)


def has_commits_to_push(repo_path: pathlib.Path, remote: str = "origin") -> bool:
    branch = _get_current_branch(repo_path)
    proc = _run_git(repo_path, ["rev-parse", "--verify", f"{remote}/{branch}"], capture=True)
    if proc.returncode != 0:
        return True
    proc2 = _run_git(repo_path, ["rev-list", "--left-right", "--count", f"{remote}/{branch}..HEAD"], capture=True)
    if proc2.returncode != 0:
        raise GitError(proc2.stderr)
    ahead_str = (proc2.stdout.strip().split()[0] if proc2.stdout else "0")
    return int(ahead_str) > 0