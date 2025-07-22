from __future__ import annotations

"""Общие утилиты (перемещены в core)."""

__all__ = ["substitute_placeholders"]


def substitute_placeholders(text: str, *, version: str, prev_version: str) -> str:
    return text.replace("{VERSION}", version).replace("{PREV_VERSION}", prev_version)