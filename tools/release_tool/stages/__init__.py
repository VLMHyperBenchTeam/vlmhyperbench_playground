"""Подпакет со стадиями release_tool.

• Основные реализации стадий теперь физически находятся внутри `release_tool/stages/`.
• Для обратной совместимости при попытке импорта мы сначала пробуем
  загрузить новый модуль (`release_tool.stages.stageN`), а если он отсутствует
  (на время поэтапной миграции), то откатываемся к старому расположению
  `release_tool.stageN`.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Final, Iterable

_STAGE_NAMES: Final[Iterable[str]] = (
    "stage0",
    "stage1",
    "stage2",
    "stage3",
    "stage4",
    "stage5",
    "stage6",
    "clear",
)

_current_pkg = __name__  # release_tool.stages

for _name in _STAGE_NAMES:
    try:
        # Пытаемся импортировать новую реализацию из подпакета stages
        _mod: ModuleType = importlib.import_module(f".{_name}", package=__name__)
    except ModuleNotFoundError:
        # На случай неполной миграции используем старый путь
        _mod = importlib.import_module(f"release_tool.{_name}")

    # Регистрируем под новым путём – так `import release_tool.stages.stageN` работает корректно
    sys.modules[f"{_current_pkg}.{_name}"] = _mod
    # Добавляем атрибут в namespace пакета для `from release_tool.stages import stageN`
    globals()[_name] = _mod  # type: ignore[assignment]

# Экспортируем список стадий как public API
__all__ = list(_STAGE_NAMES)