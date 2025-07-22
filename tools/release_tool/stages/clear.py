"""Utility: очищает каталог с файлами изменений (release_tool/changes).

Перенесён в `release_tool.stages.clear`.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

from ..config import load_config

__all__ = ["run"]


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()

    parser = argparse.ArgumentParser(description="Очистить каталог с файлами изменений (changes_output_dir)")
    parser.add_argument("--dry-run", action="store_true", help="только показать, что будет удалено, без фактического удаления")
    args = parser.parse_args(argv)

    root = pathlib.Path.cwd()
    changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes")

    if not changes_dir.exists():
        print(f"[clear] Каталог {changes_dir} не найден — ничего очищать")
        sys.exit(0)

    if args.dry_run:
        print(f"[clear] --dry-run: будет удалён каталог {changes_dir}")
        # Перечислим файлы для наглядности
        for path in changes_dir.rglob("*"):
            print(f"  {path.relative_to(root)}")
        return

    # Удаляем каталог полностью и создаём заново, чтобы сохранить структуру
    shutil.rmtree(changes_dir)
    changes_dir.mkdir(parents=True, exist_ok=True)
    print(f"[clear] ✅ Каталог {changes_dir} очищен")


if __name__ == "__main__":
    run()