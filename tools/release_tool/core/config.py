"""Конфигурация release_tool (перемещено в подпакет core).

Полный перенос из `release_tool/config.py` для упрощения архитектуры.
Старый модуль оставлен как shim для обратной совместимости.
"""
# Содержимое фактически идентично прежнему, только пути относительны.
from __future__ import annotations

import pathlib
import sys
from typing import Any, Iterator

import tomlkit  # type: ignore  # third-party


class Config(dict[str, Any]):
    """Словарь-обёртка с дефолтами и парсингом TOML."""

    _DEFAULTS: dict[str, Any] = {
        "packages_dir": "packages",
        "changes_output_dir": "release_tool/changes",
        "changes_uncommitted_filename": "changes_uncommitted.txt",
        "changes_since_tag_filename": "changes_since_tag.txt",
        "tag_message_filename": "tag_message.md",
        "staging_pyproject_path": "staging/pyproject.toml",
        "prod_pyproject_path": "prod/pyproject.toml",
        # служебное
        "dry_run": False,
    }

    def __init__(self, data: dict[str, Any] | None = None, *, source: str = "<default>") -> None:  # noqa: D401
        merged = dict(self._DEFAULTS)
        if data:
            merged.update(data)
        super().__init__(merged)
        self["_config_source"] = source

    # --- convenience --------------------------------------

    def __getattr__(self, item: str) -> Any:  # noqa: D401
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc

    def __getitem__(self, key: str) -> Any:  # type: ignore[override]
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        return super().get(key, default)

    def __repr__(self) -> str:  # noqa: D401
        return f"<Config {dict(self)!r} from {self['_config_source']}>"

    # --- parsing helpers -----------------------------------

    @classmethod
    def _iter_candidate_files(cls) -> Iterator[pathlib.Path]:
        root = pathlib.Path.cwd()
        yield root / "release_tool.toml"
        yield root / "release_tool" / "release_tool.toml"
        yield root / "pyproject.toml"
        yield pathlib.Path(__file__).resolve().parent / "release_tool.toml"

    @classmethod
    def _parse_toml(cls, path: pathlib.Path) -> dict[str, Any]:
        raw_text = path.read_text(encoding="utf-8")
        data: Any = tomlkit.parse(raw_text)
        if path.name == "pyproject.toml":
            try:
                return data["tool"]["release_tool"]
            except KeyError:
                return {}
        return data.get("tool", {}).get("release_tool", data)

    # --- public -------------------------------------------

    @classmethod
    def load(cls, config_path: str | pathlib.Path | None = None) -> "Config":
        if config_path is not None:
            path = pathlib.Path(config_path)
            if not path.exists():
                print(f"[release_tool] Конфигурационный файл не найден: {path}", file=sys.stderr)
                raise SystemExit(1)
            data = cls._parse_toml(path)
            return cls(data, source=str(path.relative_to(pathlib.Path.cwd())))

        for candidate in cls._iter_candidate_files():
            if candidate.exists():
                data = cls._parse_toml(candidate)
                return cls(data, source=str(candidate.relative_to(pathlib.Path.cwd())))

        print("[release_tool] Конфигурационный файл не найден – используются значения по умолчанию", file=sys.stderr)
        return cls()


def load_config(config_path: pathlib.Path | str | None = None) -> Config:
    """Backwards-compatible wrapper."""

    return Config.load(config_path)


__all__ = ["Config", "load_config"]