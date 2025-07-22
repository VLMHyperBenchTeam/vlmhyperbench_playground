"""Stage 1 (unstaged): собирает незакоммиченные изменения каждого пакета.

Перемещён из корня пакета в `release_tool.stages.stage1`.
"""
from __future__ import annotations

import argparse
import pathlib
from typing import Any

from ..config import load_config
from ..git_utils import (
    get_diff_stat,
    get_full_diff,
    get_uncommitted_changes,
    has_uncommitted_changes,
)
from ..core import iter_release_packages

__all__ = ["run"]


def process_package(pkg_path: pathlib.Path, cfg: dict[str, Any], dry_run: bool = False) -> None:
    # интересуют только незакоммиченные изменения
    if not has_uncommitted_changes(pkg_path):
        print(f"[stage1]   {pkg_path.name}: нет незакоммиченных изменений")
        return  # изменений нет вообще

    status = get_uncommitted_changes(pkg_path)
    diff_stat = get_diff_stat(pkg_path)
    full_diff = get_full_diff(pkg_path)

    content_parts = [
        "# Uncommitted changes (git status --porcelain)\n" + status,
        "# Diff stat (git diff --stat)\n" + diff_stat,
    ]

    if full_diff:
        content_parts.append("# Full diff (git diff)\n" + full_diff)

    content = "\n\n".join(content_parts) + "\n"

    root = pathlib.Path.cwd()
    out_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg_path.name
    out_dir.mkdir(parents=True, exist_ok=True)
    changes_file = out_dir / cfg["changes_uncommitted_filename"]
    if dry_run:
        print(f"[dry-run] would write changes to {changes_file}")
        print("==== changes ====\n" + content + "=================")
        return

    changes_file.write_text(content, encoding="utf-8")
    print(
        f"[stage1]   ✅ {pkg_path.name}: изменения сохранены в {changes_file.relative_to(pathlib.Path.cwd())}"
    )

    # Создаём пустой файл для commit-сообщения в том же каталоге
    commit_msg_file = out_dir / cfg["commit_message_filename"]
    if not commit_msg_file.exists():
        if not dry_run:
            commit_msg_file.write_text("", encoding="utf-8")
        print(
            f"[stage1]   📝 {pkg_path.name}: создан пустой файл {commit_msg_file.relative_to(pathlib.Path.cwd())}"
        )


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()

    parser = argparse.ArgumentParser(description="Stage 1: сбор изменений по пакетам")
    parser.add_argument("--dry-run", action="store_true", help="только показать действия, без записи файлов")
    args = parser.parse_args(argv)

    print("[stage1] Поиск незакоммиченных изменений в пакетах...")
    print(f"[stage1] Конфигурация: {cfg.get('_config_source', 'неизвестно')}")

    packages_iter = iter_release_packages(cfg, include_all=True)

    changed = 0
    for pkg in packages_iter:
        print(f"[stage1] Проверяем пакет: {pkg.name}")
        process_package(pkg.path, cfg, dry_run=args.dry_run or cfg.get("dry_run", False))

        changes_file = pkg.changes_dir / cfg["changes_uncommitted_filename"]
        if changes_file.exists():
            changed += 1

    if changed == 0:
        print("[stage1] ✅ Изменений не обнаружено — файлы изменений не созданы")
    else:
        print(f"[stage1] ✅ Завершено. Обработано пакетов с изменениями: {changed}")
        print(f"[stage1] Файлы изменений сохранены в: {cfg.get('changes_output_dir', 'release_tool/changes')}")


if __name__ == "__main__":
    run()