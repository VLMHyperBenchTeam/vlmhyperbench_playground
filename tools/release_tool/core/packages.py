from __future__ import annotations

"""Helpers для работы с пакетами workspace (перемещено в core)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Any

__all__ = ["Package", "iter_release_packages"]


@dataclass(slots=True)
class Package:
    name: str
    path: Path
    changes_dir: Path
    pyproject: Path

    def __str__(self) -> str:  # noqa: D401
        return f"<Package {self.name} at {self.path}>"


def iter_release_packages(cfg: dict[str, Any], *, include_all: bool = True) -> Iterator[Package]:
    root = Path.cwd()
    packages_dir = root / cfg.get("packages_dir", "packages")
    if not packages_dir.is_dir():
        return
    changes_root = root / cfg.get("changes_output_dir", "release_tool/changes")
    for pkg_path in sorted(packages_dir.iterdir()):
        if not pkg_path.is_dir():
            continue
        if not include_all and not (changes_root / pkg_path.name).exists():
            continue
        yield Package(
            name=pkg_path.name,
            path=pkg_path,
            changes_dir=changes_root / pkg_path.name,
            pyproject=pkg_path / "pyproject.toml",
        )