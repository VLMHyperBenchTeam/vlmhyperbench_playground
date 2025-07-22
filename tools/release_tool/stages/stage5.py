"""Stage 5: ставит аннотированный тег на release-коммит и обновляет prod/pyproject.toml.

Перенесён в `release_tool.stages.stage5`.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Optional

import tomlkit  # type: ignore  # third-party

from ..config import load_config
from ..git_utils import GitError, _run_git, commit_all
from ..utils import substitute_placeholders

DEFAULT_TAG_TMPL = """## Релиз {VERSION}

_Изменения по сравнению с {PREV_VERSION}_

<!-- Опишите основные изменения здесь -->
"""

__all__ = ["run"]


# noinspection PyMissingOrEmptyDocstring
def _is_default_tag_message(text: str) -> bool:
    """Возвращает True, если файл tag_message.md не изменён пользователем."""
    return text.strip() == DEFAULT_TAG_TMPL.strip()


def _get_package_version(pyproject: pathlib.Path) -> str:
    """Возвращает текущую версию пакета из pyproject.toml через tomlkit."""
    doc = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    try:
        return str(doc["project"]["version"])
    except KeyError as exc:
        raise RuntimeError("version field not found") from exc


def _tag_exists(repo: pathlib.Path, tag: str) -> bool:
    proc = _run_git(repo, ["tag", "-l", tag])
    return bool(proc.stdout.strip())


# --- helpers for prod pyproject -------------------------------------------------


def _update_dependency_tag(pyproject: pathlib.Path, dep_name: str, new_tag: str, dry_run: bool = False) -> bool:
    """Обновляет `tag` у зависимости *dep_name* в [tool.uv.sources] через tomlkit.

    Возвращает True, если файл был изменён.
    """
    if not pyproject.exists():
        return False

    doc = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    changed = False
    try:
        sources_tbl = doc["tool"]["uv"]["sources"]
        if dep_name in sources_tbl:
            entry = sources_tbl[dep_name]
            if entry.get("tag") != new_tag:
                entry["tag"] = new_tag
                changed = True
    except KeyError:
        pass

    if changed and not dry_run:
        pyproject.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return changed


def _create_tag(repo: pathlib.Path, tag: str, message: str, push: bool, dry_run: bool) -> None:
    if dry_run:
        print(f"[stage5]   [dry-run] git -C {repo} tag -a {tag} -m \"{message.splitlines()[0]}…\"")
        if push:
            print(f"[stage5]   [dry-run] git -C {repo} push origin {tag}")
        return
    proc = _run_git(repo, ["tag", "-a", tag, "-m", message], capture=False)
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    if push:
        proc = _run_git(repo, ["push", "origin", tag], capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr)


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 5: create and push annotated tag + update prod pyproject")
    parser.add_argument("--push", action="store_true", help="git push тег после создания (а также коммит prod)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--base-branch", default="main", help="Целевая ветка, в которой находится релизный коммит")
    parser.add_argument("--delete-branch", help="Локальная ветка, которую удалить после успешного merge")
    parser.add_argument("--sync", action="store_true", help="Перед тегированием выполнить fetch/checkout/pull base-branch и (опц.) удалить dev-ветку")
    parser.add_argument("--remote", default=cfg.get("git_remote", "origin"), help="Имя удалённого репозитория")
    args = parser.parse_args(argv)

    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage5] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    prod_py_path = root / cfg.get("prod_pyproject_path", "prod/pyproject.toml")
    prod_changed_any = False

    # Обрабатываем только те пакеты, для которых release_tool/changes/<pkg> существует
    changes_root = root / cfg.get("changes_output_dir", "release_tool/changes")

    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue

        pkg_changes_dir = changes_root / pkg.name
        if not pkg_changes_dir.exists():
            # У пакета нет изменений в текущем релизе → пропускаем
            continue

        pyproject = pkg / "pyproject.toml"
        if not pyproject.exists():
            continue

        version = _get_package_version(pyproject)
        tag_name = f"{cfg.get('tag_prefix', '')}{version}"
        print(f"[stage5] Обрабатываем пакет: {pkg.name} → {tag_name}")
        if _tag_exists(pkg, tag_name):
            print("[stage5]   🟡 тег уже существует, пропускаем")
            continue
        # Используем содержимое tag_message.md, если он есть; иначе — сообщение последнего коммита
        tag_msg_file = pkg_changes_dir / cfg["tag_message_filename"]
        raw_msg: str = ""
        if tag_msg_file.exists():
            candidate = tag_msg_file.read_text(encoding="utf-8")
            if _is_default_tag_message(candidate):
                print(f"[stage5]   {pkg.name}: файл tag-сообщения не изменён – пропускаем")
                continue  # переходим к следующему пакету
            raw_msg = candidate.strip()
        # если сообщение пустое – возьмём из последнего коммита
        if not raw_msg:
            proc = _run_git(pkg, ["log", "-1", "--pretty=%B"])
            raw_msg = proc.stdout.strip() or f"Release {tag_name}"

        # Подстановка плейсхолдеров через общий helper
        commit_msg = substitute_placeholders(raw_msg, version=version, prev_version=version)

        # --- prod pyproject update (root repo) -----------------------------
        # Определяем project name через tomlkit
        pkg_project_name: Optional[str] = None
        try:
            doc_pkg = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
            pkg_project_name = str(doc_pkg["project"]["name"])
        except KeyError:
            pkg_project_name = None
        if pkg_project_name:
            changed_prod = _update_dependency_tag(prod_py_path, pkg_project_name, tag_name, dry_run=args.dry_run or cfg.get("dry_run", False))
            prod_changed_any = prod_changed_any or changed_prod
            if changed_prod:
                print(f"[stage5]   📝 prod/pyproject.toml обновлён → {pkg_project_name}={tag_name}")

        # optional sync checkout
        if args.sync:
            remote_name = args.remote
            _run_git(pkg, ["fetch", remote_name], capture=False)
            _run_git(pkg, ["checkout", args.base_branch], capture=False)
            _run_git(pkg, ["pull", remote_name, args.base_branch], capture=False)
            if args.delete_branch:
                _run_git(pkg, ["branch", "-D", args.delete_branch], capture=False)

        _create_tag(
            pkg,
            tag_name,
            commit_msg,
            push=args.push,
            dry_run=args.dry_run or cfg.get("dry_run", False),
        )
        print("[stage5]   ✅ тег создан")
        # Вывод ссылки на тег для удобного копирования
        if args.push and not (args.dry_run or cfg.get("dry_run", False)):
            # Получаем URL удалённого репозитория
            proc_url = _run_git(pkg, ["config", "--get", f"remote.{args.remote}.url"])
            remote_url = proc_url.stdout.strip()

            def _to_https(url: str) -> str | None:
                """Конвертирует ssh/https git-URL в https-URL без .git"""
                if url.startswith("git@"):
                    _, rest = url.split("@", 1)
                    host, path = rest.split(":", 1)
                    path = path[:-4] if path.endswith(".git") else path
                    return f"https://{host}/{path}"
                if url.startswith("https://") or url.startswith("http://"):
                    return url.removesuffix(".git")
                return None

            base_url = _to_https(remote_url)
            if base_url:
                print(f"[stage5]   🔗 {base_url}/releases/tag/{tag_name}")
        processed += 1

    # Commit prod pyproject once if changed
    if prod_changed_any:
        if args.dry_run or cfg.get("dry_run", False):
            print(f"[stage5]   [dry-run] git add {prod_py_path}")
            print("[stage5]   [dry-run] git commit -m \"chore(prod): update dependencies\"")
            if args.push:
                print(f"[stage5]   [dry-run] git push {args.remote}")
        else:
            try:
                commit_all(root, "chore(prod): update dependencies", remote=args.remote, push=args.push)
                print("[stage5]   ✅ prod/pyproject.toml коммитнут")
            except Exception as exc:
                print(f"[stage5]   ❌ commit prod error: {exc}")

    print(f"[stage5] ✅ Завершено. Обработано пакетов: {processed}")


if __name__ == "__main__":
    run()