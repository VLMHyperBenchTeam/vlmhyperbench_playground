"""Stage 6: начинает новый dev-цикл после релиза.

Перенесён в `release_tool.stages.stage6`.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import tomlkit  # type: ignore  # third-party
from packaging.version import InvalidVersion, Version  # type: ignore

from ..config import load_config
from ..git_utils import _push_repo, _run_git

__all__ = ["run"]


def _next_dev_version(release_version: str) -> str:
    try:
        v = Version(release_version)
    except InvalidVersion as exc:
        raise ValueError(f"Invalid release version: {release_version}") from exc

    # если уже dev → +1
    if v.dev is not None:
        num = v.dev + 1 if isinstance(v.dev, int) else 1
        prefix = str(v).split(".dev")[0]
        return f"{prefix}.dev{num}"

    release = list(v.release) + [0, 0]
    major, minor, patch = release[:3]
    patch += 1
    return f"{major}.{minor}.{patch}.dev0"


def _get_current_version(pyproject: pathlib.Path) -> str:
    """Возвращает текущую версию из pyproject.toml (tomlkit)."""
    doc = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    try:
        return str(doc["project"]["version"])
    except KeyError as exc:
        raise RuntimeError("version field not found") from exc


def _set_version(pyproject: pathlib.Path, new_version: str) -> None:
    doc = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    try:
        doc["project"]["version"] = new_version
    except KeyError as exc:
        raise RuntimeError("version field not found") from exc
    pyproject.write_text(tomlkit.dumps(doc), encoding="utf-8")


def _process_package(pkg_path: pathlib.Path, branch: str, push: bool, remote: str, dry_run: bool) -> None:
    pyproject = pkg_path / "pyproject.toml"
    if not pyproject.exists():
        return
    current_version = _get_current_version(pyproject)
    next_dev = _next_dev_version(current_version)

    if dry_run:
        print(f"[stage6]   [dry-run] {pkg_path.name}: {current_version} -> {next_dev}")
        print(
            f"[stage6]   [dry-run] git -C {pkg_path} checkout -B {branch} origin/main || git checkout {branch}"
        )
        print(f"[stage6]   [dry-run] commit 'chore: start {next_dev} development'")
        return

    # checkout / create branch
    proc = _run_git(pkg_path, ["checkout", "-B", branch, "origin/main"], capture=True)
    if proc.returncode != 0:
        # fallback: maybe branch exists locally
        _run_git(pkg_path, ["checkout", "-B", branch], capture=False)

    _set_version(pyproject, next_dev)
    _run_git(pkg_path, ["add", str(pyproject.relative_to(pkg_path))], capture=False)
    _run_git(pkg_path, ["commit", "-m", f"chore: start {next_dev} development"], capture=False)

    if push:
        _push_repo(pkg_path, remote)
        print(f"[stage6]   🚀 ветка {branch} отправлена")

    print(f"[stage6]   ✅ {pkg_path.name}: начат dev-цикл {next_dev}")


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 6: start next dev cycle")
    parser.add_argument("--branch", default="dev_branch", help="Имя ветки для dev-цикла")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--remote", default=cfg.get("git_remote", "origin"), help="Имя удалённого репозитория для push")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage6] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    # Фильтруем пакеты по наличию каталога изменений
    changes_root = root / cfg.get("changes_output_dir", "release_tool/changes")

    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue

        if not (changes_root / pkg.name).exists():
            # пакет не участвовал в текущем релизе
            continue

        print(f"[stage6] Обрабатываем пакет: {pkg.name}")
        _process_package(
            pkg,
            args.branch,
            push=args.push,
            remote=args.remote,
            dry_run=args.dry_run or cfg.get("dry_run", False),
        )
        processed += 1

    print(f"[stage6] ✅ Завершено. Обработано пакетов: {processed}")


if __name__ == "__main__":
    run()