"""Stage 2: делает коммит и/или push изменений во всех пакетах.
Перенесён в `release_tool.stages.stage2`.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

from ..config import load_config
from ..git_utils import _push_repo, commit_all, _get_current_branch
from ..status_analyzer import analyze_repo_status, RepoStatus

__all__ = ["run"]


def process_package(pkg_path: pathlib.Path, cfg: dict[str, Any], push: bool, dry_run: bool = False) -> RepoStatus | None:
    """Создаёт commit и/или push для *pkg_path* и возвращает итоговый RepoStatus."""

    root = pathlib.Path.cwd()
    changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg_path.name
    msg_file = changes_dir / cfg["commit_message_filename"]
    if not msg_file.exists():
        print(f"[stage2]   {pkg_path.name}: файл commit-сообщения не найден")
        return None

    message = msg_file.read_text(encoding="utf-8").strip()
    if not message:
        print(f"[stage2]   {pkg_path.name}: пустое commit-сообщение")
        return None

    commit_all(pkg_path, message, remote=cfg.get("git_remote", "origin"), push=push, dry_run=dry_run)

    branch = _get_current_branch(pkg_path)
    repo_status = analyze_repo_status(pkg_path, branch, cfg.get("git_remote", "origin"))

    status_parts: list[str] = []
    if repo_status.ahead:
        status_parts.append(f"ahead:{repo_status.ahead}")
    if repo_status.behind:
        status_parts.append(f"behind:{repo_status.behind}")
    if repo_status.uncommitted:
        status_parts.append("uncommitted")

    status_str = ", ".join(status_parts) if status_parts else "ok"
    print(f"[stage2]   ✅ {pkg_path.name}: commit создан{' и отправлен' if push else ''}; {status_str}")
    return repo_status


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()

    parser = argparse.ArgumentParser(description="Stage 2: commit и/или push изменений по пакетам")
    parser.add_argument("--commit", action="store_true", help="создать коммит по подготовленным сообщениям")
    parser.add_argument("--push", action="store_true", help="выполнить git push для пакетов")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.commit and not args.push:
        args.commit = True  # по умолчанию только commit

    actions_descr = [act for act, flag in (("коммит", args.commit), ("push", args.push)) if flag]
    print(f"[stage2] Выполняем {' и '.join(actions_descr)} для пакетов с подготовленными сообщениями…")

    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage2] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
        print(f"[stage2] Проверяем пакет: {pkg.name}")

        changes_root = root / cfg.get("changes_output_dir", "release_tool/changes")
        in_current_release = (changes_root / pkg.name).exists()

        if args.commit:
            process_package(pkg, cfg, push=False, dry_run=args.dry_run or cfg.get("dry_run", False))

        if args.push:
            if not in_current_release:
                print(f"[stage2]   ⏩ {pkg.name}: не участвует в релизе — push пропущен")
            else:
                remote_name = cfg.get("git_remote", "origin")
                try:
                    repo_status = analyze_repo_status(pkg, _get_current_branch(pkg), remote_name)
                    if repo_status.ahead:
                        _push_repo(pkg, remote_name)
                        print(f"[stage2]   ✅ {pkg.name}: изменения отправлены (остался behind:{repo_status.behind})")
                    else:
                        print(f"[stage2]   📭 {pkg.name}: изменений нет (ahead:0)")
                except Exception as exc:  # noqa: BLE001
                    print(f"[stage2]   ❌ {pkg.name}: push завершился ошибкой: {exc}")

        msg_file = (changes_root / pkg.name / cfg["commit_message_filename"])
        if args.commit and msg_file.exists() and msg_file.read_text(encoding="utf-8").strip():
            processed += 1

    if processed == 0:
        print("[stage2] ✅ Нет пакетов с подготовленными commit-сообщениями")
    else:
        print(f"[stage2] ✅ Завершено. Обработано пакетов: {processed}")


if __name__ == "__main__":
    run()