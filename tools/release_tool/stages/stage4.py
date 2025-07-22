"""Stage 4: делает *release*-коммит без тега.

Перенесён в `release_tool.stages.stage4`.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Any

import tomlkit  # type: ignore  # third-party
from packaging.version import InvalidVersion, Version  # type: ignore

from ..config import load_config
from ..git_utils import (
    GitError,
    _push_repo,
    _run_git,
    commit_all,
)
from ..utils import substitute_placeholders

_SEMVER_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
_DEV_RE = re.compile(r"^(?P<prefix>.*?)(?P<dev>\.dev(?P<num>\d+))?$")

DEFAULT_TAG_TMPL = """## Релиз {VERSION}

_Изменения по сравнению с {PREV_VERSION}_

<!-- Опишите основные изменения здесь -->
"""

__all__ = ["run"]


def _is_default_tag_message(text: str) -> bool:
    """Возвращает True, если файл tag_message.md не изменён пользователем."""
    return text.strip() == DEFAULT_TAG_TMPL.strip()


def bump_dev(version_str: str) -> str:
    try:
        _ = Version(version_str)
    except InvalidVersion as exc:
        raise ValueError(f"Invalid version: {version_str}") from exc
    m = _DEV_RE.match(version_str)
    if not m:
        raise ValueError("bad version")
    prefix = m.group("prefix")
    num = int(m.group("num") or 0) + 1
    return f"{prefix}.dev{num}"


def bump_semver(version_str: str, part: str) -> str:
    """Bump release part ignoring suffixes (.devN)"""

    try:
        v = Version(version_str)
    except InvalidVersion as exc:
        raise ValueError(f"Invalid version: {version_str}") from exc

    release = list(v.release) + [0, 0]
    major, minor, patch = release[:3]

    # Если dev-версия → завершить текущий релиз без увеличения patch
    if v.dev is not None and part == "patch":
        return f"{major}.{minor}.{patch}"

    if part == "patch":
        patch += 1
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "major":
        major += 1
        minor = patch = 0
    else:
        raise ValueError("unknown part")

    return f"{major}.{minor}.{patch}"


def bump_version(version_str: str, part: str) -> str:
    if part == "dev":
        return bump_dev(version_str)
    return bump_semver(version_str, part)


def _clean_workspace_sources(pyproject: pathlib.Path, dry_run: bool = False) -> None:
    """Удаляет ключ `workspace = true` из элементов [tool.uv.sources] с помощью tomlkit."""
    doc = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    changed = False
    try:
        sources_table = doc["tool"]["uv"]["sources"]
        # tomlkit возвращает TomlTable, поддерживающий dict-интерфейс
        for name, tbl in list(sources_table.items()):
            if isinstance(tbl, (dict, tomlkit.items.Table)):
                if tbl.get("workspace") is True:
                    del tbl["workspace"]
                    # если больше нет полей – удаляем источник целиком
                    if len(tbl) == 0:
                        del sources_table[name]
                    changed = True

        # Если после удаления всех записей таблица sources оказалась пустой – убираем всю секцию
        if len(sources_table) == 0:
            # Удаляем уровень sources
            del doc["tool"]["uv"]["sources"]
            # Если таблица uv теперь тоже пуста – удаляем и её
            if len(doc["tool"]["uv"]) == 0:
                del doc["tool"]["uv"]
            changed = True
    except KeyError:
        # секция может отсутствовать – ничего не меняем
        pass

    if changed and not dry_run:
        pyproject.write_text(tomlkit.dumps(doc), encoding="utf-8")


def update_version_in_pyproject(pyproject: pathlib.Path, new_version: str) -> None:
    """Обновляет поле project.version через tomlkit."""
    doc = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    try:
        if doc["project"]["version"] == new_version:  # noqa: SIM118
            return  # version уже актуальна
        doc["project"]["version"] = new_version
    except KeyError as exc:  # pragma: no cover – структура pyproject нарушена
        raise RuntimeError("version field not found in pyproject.toml") from exc

    pyproject.write_text(tomlkit.dumps(doc), encoding="utf-8")


# --- helpers for staging pyproject -------------------------------------------------


def _update_dependency_tag(pyproject: pathlib.Path, dep_name: str, new_tag: str, dry_run: bool = False) -> bool:
    """Обновляет значение `tag` в [tool.uv.sources.<dep_name>] через tomlkit.

    Возвращает True, если файл был изменён.
    """
    if not pyproject.exists():
        return False

    doc = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    changed = False
    try:
        src_tbl = doc["tool"]["uv"]["sources"]
        if dep_name in src_tbl:
            dep_entry = src_tbl[dep_name]
            if dep_entry.get("tag") != new_tag:
                dep_entry["tag"] = new_tag
                changed = True
    except KeyError:
        pass  # секция sources отсутствует

    if changed and not dry_run:
        pyproject.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return changed


def _process_package(pkg_path: pathlib.Path, cfg: dict[str, Any], bump_part: str, push: bool, dry_run: bool) -> bool:
    """Обрабатывает пакет. Возвращает True, если staging/pyproject.toml был изменён."""
    root = pathlib.Path.cwd()
    changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg_path.name
    tag_msg_file = changes_dir / cfg["tag_message_filename"]
    if not tag_msg_file.exists() or not tag_msg_file.read_text(encoding="utf-8").strip():
        print(f"[stage4]   {pkg_path.name}: файл tag-сообщения не найден или пуст")
        return False
    raw_tag_msg = tag_msg_file.read_text(encoding="utf-8")
    if _is_default_tag_message(raw_tag_msg):
        print(f"[stage4]   {pkg_path.name}: файл tag-сообщения не изменён – пропущен")
        return False
    raw_tag_msg = raw_tag_msg.strip()

    pyproject = pkg_path / "pyproject.toml"
    if not pyproject.exists():
        print(f"[stage4]   {pkg_path.name}: pyproject.toml не найден")
        return False

    # Читаем pyproject через tomlkit
    try:
        doc_pkg = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
        project_name = str(doc_pkg["project"]["name"])
        current_version = str(doc_pkg["project"]["version"])
    except KeyError:
        print(f"[stage4]   {pkg_path.name}: имя или версия не найдены в pyproject.toml")
        return False

    new_version = bump_version(current_version, bump_part)

    # Подставляем плейсхолдеры в сообщении
    tag_message = substitute_placeholders(raw_tag_msg, version=new_version, prev_version=current_version)

    if dry_run:
        print(f"[stage4]   [dry-run] {pkg_path.name}: {current_version} -> {new_version}")
        print(f"[stage4]   [dry-run] git -C {pkg_path} add -A")
        print(f"[stage4]   [dry-run] git -C {pkg_path} commit -m <tag_message>")
    else:
        print(f"[stage4]   📦 {pkg_path.name}: {current_version} -> {new_version}")
        update_version_in_pyproject(pyproject, new_version)
        _clean_workspace_sources(pyproject)

        # commit in package repo
        proc = _run_git(pkg_path, ["add", "-A"], capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr)
        proc = _run_git(pkg_path, ["commit", "-m", tag_message], capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr)
        print(f"[stage4]   ✅ commit создан: {new_version}")

        if push:
            if dry_run:
                print(f"[stage4]   [dry-run] git -C {pkg_path} push {cfg.get('git_remote', 'origin')}")
            else:
                try:
                    _push_repo(pkg_path, cfg.get("git_remote", "origin"))
                    print(f"[stage4]   🚀 {pkg_path.name}: изменения отправлены")
                    # После успешного push выводим ссылку на создание Pull Request
                    remote_name = cfg.get("git_remote", "origin")
                    proc_url = _run_git(pkg_path, ["config", "--get", f"remote.{remote_name}.url"])
                    remote_url = proc_url.stdout.strip()

                    def _to_https(url: str) -> str | None:
                        """Конвертирует ssh/https git-URL в https-URL без .git."""
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
                        # Определяем текущую ветку (обычно dev_branch)
                        proc_branch = _run_git(pkg_path, ["rev-parse", "--abbrev-ref", "HEAD"])
                        branch_curr = proc_branch.stdout.strip()
                        if branch_curr:
                            print(f"[stage4]   🔗 Создать PR: {base_url}/compare/{branch_curr}?expand=1")
                except Exception as exc:  # noqa: BLE001
                    print(f"[stage4]   ❌ push error: {exc}")

    # --- staging pyproject update ------------------------
    staging_py_path = root / cfg.get("staging_pyproject_path", "staging/pyproject.toml")
    changed_staging = _update_dependency_tag(staging_py_path, project_name, new_version, dry_run=dry_run)
    if changed_staging:
        print(f"[stage4]   📝 staging/pyproject.toml обновлён → {project_name}={new_version}")
    return changed_staging


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 4 (prepare release): commit without tag and update staging pyproject")
    parser.add_argument("--bump", choices=["patch", "minor", "major", "dev"], help="Какая часть версии")
    parser.add_argument("--push", action="store_true", help="Выполнить git push (с опциональным bump-коммитом)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage4] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    if args.bump:
        print(f"[stage4] Выполняем prepare-release bump ({args.bump})…")
    elif args.push:
        print("[stage4] Выполняем push изменений без bump…")
    else:
        print("[stage4] Ничего делать не нужно: не указан --bump и --push. Завершено.")
        return

    processed = 0
    staging_changed_any = False
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
        if args.bump:
            print(f"[stage4] Обрабатываем пакет: {pkg.name}")
            changed = _process_package(pkg, cfg, args.bump, push=args.push, dry_run=args.dry_run or cfg.get("dry_run", False))
            staging_changed_any = staging_changed_any or changed
            processed += 1
        elif args.push:
            # режим push-only
            if args.dry_run or cfg.get("dry_run", False):
                print(f"[stage4]   [dry-run] git -C {pkg} push {cfg.get('git_remote', 'origin')}")
            else:
                try:
                    _push_repo(pkg, cfg.get("git_remote", "origin"))
                    print(f"[stage4]   🚀 {pkg.name}: изменения отправлены")
                except Exception as exc:  # noqa: BLE001
                    print(f"[stage4]   ❌ push error: {exc}")
            processed += 1

    # commit root staging pyproject if changed (только при bump)
    if staging_changed_any:
        staging_py_path = root / cfg.get("staging_pyproject_path", "staging/pyproject.toml")
        if args.dry_run or cfg.get("dry_run", False):
            print(f"[stage4]   [dry-run] git add {staging_py_path}")
            print("[stage4]   [dry-run] git commit -m \"chore(staging): update dependencies\"")
            if args.push:
                print(f"[stage4]   [dry-run] git push {cfg.get('git_remote', 'origin')}")
        else:
            try:
                commit_all(root, "chore(staging): update dependencies", remote=cfg.get("git_remote", "origin"), push=args.push)
                print("[stage4]   ✅ staging/pyproject.toml коммитнут")
            except Exception as exc:
                print(f"[stage4]   ❌ commit staging error: {exc}")

    print(f"[stage4] ✅ Завершено. Обработано пакетов: {processed}")


if __name__ == "__main__":
    run()