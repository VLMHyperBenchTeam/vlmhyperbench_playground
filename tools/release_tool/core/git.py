from __future__ import annotations

"""Упрощённый фасад GitRepo (перемещён в подпакет core)."""

from pathlib import Path

from .git_utils import _run_git, GitError

__all__ = ["GitRepo"]


class GitRepo:  # noqa: D101 – simple façade
    def __init__(self, path: str | Path) -> None:  # noqa: D401
        self.path = Path(path).resolve()
        if not (self.path / ".git").exists():
            raise ValueError(f"{self.path} is not a git repository")

    def run(self, *args: str, capture: bool = True) -> str:
        proc = _run_git(self.path, list(args), capture=capture)
        if proc.returncode != 0:
            raise GitError(proc.stderr or proc.stdout)
        return proc.stdout.strip() if capture else ""

    def fetch(self, remote: str = "origin") -> "GitRepo":
        self.run("fetch", remote, capture=False)
        return self

    def fast_forward(self, ref: str) -> "GitRepo":
        try:
            self.run("merge", "--ff-only", ref, capture=False)
        except GitError as exc:
            raise RuntimeError(f"Cannot fast-forward {self.path.name}: {exc}") from exc
        return self

    def push(self, remote: str = "origin", branch: str | None = None) -> "GitRepo":
        args = ["push", remote] + ([branch] if branch else [])
        self.run(*args, capture=False)
        return self

    def current_branch(self) -> str:
        return self.run("rev-parse", "--abbrev-ref", "HEAD")