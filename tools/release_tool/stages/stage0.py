from __future__ import annotations

"""Stage 0: подготавливает dev-ветки в пакетах перед началом релизного цикла.

Физически перемещён из корня пакета в ``release_tool.stages.stage0``.
"""

import argparse
import pathlib
import sys
from dataclasses import dataclass

from ..config import load_config
from ..git_utils import _push_repo, _run_git, has_commits_to_push, GitError
from ..git_helpers import (
    remote_branch_exists,
    local_branch_exists,
    fast_forward,
    checkout_branch,
    ensure_tracking,
    temporary_stash,
)
from ..status_analyzer import analyze_repo_status, RepoStatus
from ..core import iter_release_packages

__all__ = ["run"]


@dataclass
class PackageResult:
    name: str
    push_done: bool
    stash_kept: bool
    ahead: int
    behind: int
    uncommitted: bool


# --- internal helpers ---------------------------------------------------------

def _process_package(
    pkg: pathlib.Path,
    branch: str,
    base: str,
    remote: str,
    push: bool,
    dry_run: bool,
    no_stash: bool,
    stash_name: str,
    keep_stash: bool,
    fallback_head: bool,
    fallback_local: bool,
) -> tuple[bool, bool, RepoStatus]:
    """Готовит dev-ветку *branch* в пакете *pkg* и возвращает итоговый статус."""

    # --- dry-run --------------------------------------------------------------
    if dry_run:
        print(f"[stage0]   [dry-run] git -C {pkg} fetch {remote}")
        print(f"[stage0]   [dry-run] git -C {pkg} checkout -B {branch} {remote}/{base}")
        if push:
            print(f"[stage0]   [dry-run] git -C {pkg} push --set-upstream {remote} {branch}")
        dummy_status = RepoStatus(ahead=0, behind=0, uncommitted=False)
        return False, False, dummy_status

    # -------------------------------------------------------------------------
    _run_git(pkg, ["fetch", remote], capture=False)

    remote_dev_exists = remote_branch_exists(pkg, remote, branch)
    local_dev_exists = local_branch_exists(pkg, branch)

    stash_kept = False

    if remote_dev_exists:
        # --- существующая ветка на remote ------------------------------------
        start_point = None if local_dev_exists else f"{remote}/{branch}"
        checkout_branch(pkg, branch, start_point)

        try:
            fast_forward(pkg, f"{remote}/{branch}")
        except GitError:
            print(
                f"[stage0]   ⚠️  {pkg.name}: локальная {branch} расходится с {remote}/{branch} — manual rebase/push"
            )

    else:
        # --- создаём dev из base ---------------------------------------------
        # Определяем ref, от которого будем создавать ветку.
        if remote_branch_exists(pkg, remote, base):
            start_ref = f"{remote}/{base}"
        elif fallback_head:
            head_proc = _run_git(pkg, ["symbolic-ref", f"refs/remotes/{remote}/HEAD"], capture=True)
            if head_proc.returncode == 0:
                default = head_proc.stdout.strip().split("/")[-1] or base
                print(f"[stage0]   ℹ️  {pkg.name}: используем дефолтную ветку {default} вместо {base}")
                start_ref = f"{remote}/{default}"
            elif fallback_local:
                start_ref = base  # локальный base
            else:
                start_ref = base
        else:
            start_ref = base

        # Проверяем, нужны ли stash-операции.
        workspace_dirty = bool(_run_git(pkg, ["status", "--porcelain"], capture=True).stdout.strip())
        if workspace_dirty and no_stash:
            print(
                f"[stage0]   ❌ {pkg.name}: есть незакоммиченные изменения, --no-stash установлен — пакет пропущен"
            )
            dummy_status = RepoStatus(ahead=0, behind=0, uncommitted=False)
            return False, False, dummy_status

        with temporary_stash(
            pkg,
            enabled=workspace_dirty and not no_stash,
            message=stash_name,
            keep=keep_stash,
        ) as ts:
            checkout_branch(pkg, branch, start_ref)
        stash_kept = ts.kept

    # --- настройка upstream ---------------------------------------------------
    ensure_tracking(pkg, branch, remote)

    # --- push -----------------------------------------------------------------
    push_done = False
    if push and has_commits_to_push(pkg, remote):
        _push_repo(pkg, remote)
        print(f"[stage0]   🚀 ветка {branch} отправлена")
        push_done = True
    elif push:
        print("[stage0]   📭 изменений нет — push пропущен")

    # --- анализ состояния ветки ----------------------------------------------
    repo_status = analyze_repo_status(pkg, branch, remote)

    print(f"[stage0]   ✅ {pkg.name}: подготовлена ветка {branch} (от {base})")

    return push_done, stash_kept, repo_status


# --- entrypoint --------------------------------------------------------------

def run(argv: list[str] | None = None) -> None:
    cfg = load_config()

    parser = argparse.ArgumentParser(description="Stage 0: prepare dev branches from base branch")
    parser.add_argument("--branch", default="dev_branch", help="Имя dev-ветки")
    parser.add_argument("--base-branch", default="main", help="Базовая ветка, от которой создаётся dev-ветка")
    parser.add_argument("--push", action="store_true", help="Отправить ветку после создания")
    parser.add_argument("--dry-run", action="store_true")
    # дополнительные флаги
    parser.add_argument("--no-stash", action="store_true", help="Не выполнять auto-stash, если есть изменения (завершить ошибкой)")
    parser.add_argument("--stash-name", help="Пользовательский заголовок stash, по умолчанию stage0-auto-<branch>")
    parser.add_argument("--keep-stash", action="store_true", help="Не удалять созданный stash после успешного pop без конфликтов")
    parser.add_argument(
        "--fallback-head",
        dest="fallback_head",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Использовать origin/HEAD если <base_branch> не найден",
    )
    parser.add_argument(
        "--fallback-local",
        dest="fallback_local",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Использовать локальную ветку <base_branch> если remote отсутствует",
    )
    args = parser.parse_args(argv)

    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage0] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    remote_name = cfg.get("git_remote", "origin")

    processed = 0
    results: list[PackageResult] = []
    for pkg_info in iter_release_packages(cfg, include_all=False):
        pkg = pkg_info.path
        # Проверяем, что remote существует
        remote_chk = _run_git(pkg, ["remote", "get-url", remote_name])
        if remote_chk.returncode != 0:
            print(f"[stage0]   ❌ {pkg.name}: remote '{remote_name}' не найден — пропуск")
            continue

        print(f"[stage0] Обрабатываем пакет: {pkg.name}")
        push_done, stash_kept, repo_status = _process_package(
            pkg,
            args.branch,
            args.base_branch,
            remote_name,
            args.push,
            dry_run=args.dry_run or cfg.get("dry_run", False),
            no_stash=args.no_stash,
            stash_name=args.stash_name or f"stage0-auto-{args.branch}",
            keep_stash=args.keep_stash,
            fallback_head=args.fallback_head,
            fallback_local=args.fallback_local,
        )
        results.append(
            PackageResult(
                name=pkg.name,
                push_done=push_done,
                stash_kept=stash_kept,
                ahead=repo_status.ahead,
                behind=repo_status.behind,
                uncommitted=repo_status.uncommitted,
            )
        )
        processed += 1

    # итоговый отчёт -----------------------------------------------------------
    lines: list[str] = []
    for r in results:
        parts: list[str] = []
        if r.ahead:
            parts.append(f"ahead:{r.ahead}")
        if r.behind:
            parts.append(f"behind:{r.behind}")
        if r.stash_kept:
            parts.append("stash")
        if r.uncommitted:
            parts.append("uncommitted")
        status = ", ".join(parts) if parts else "ok"
        push_status = "отправлена" if r.push_done else "локально"
        lines.append(f"  • {r.name:<15} — {push_status}; {status}")

    print(f"[stage0] ✅ Завершено. Обработано пакетов: {processed}\n[stage0] Итог:\n" + "\n".join(lines))


if __name__ == "__main__":
    run()