import importlib as _importlib
import sys

# ---------------------------------------------------------------------------
# Динамический реэкспорт core-модулей (должен быть ДО импорта stages)
# ---------------------------------------------------------------------------
for _m in (
    "config",
    "git",
    "git_utils",
    "git_helpers",
    "packages",
    "status_analyzer",
    "utils",
):
    _mod_full = f"release_tool.core.{_m}"
    _mod = _importlib.import_module(_mod_full)
    sys.modules[f"release_tool.{_m}"] = _mod

# Упрощаем «star import» для стадий
_stages = _importlib.import_module("release_tool.stages")

for _stage in (
    "stage0",
    "stage1",
    "stage2",
    "stage3",
    "stage4",
    "stage5",
    "stage6",
    "clear",
):
    _stage_mod = _importlib.import_module(f"release_tool.stages.{_stage}")
    sys.modules[f"release_tool.{_stage}"] = _stage_mod

__all__ = [
    "core",
    "stages",
    "config",
    "git",
    "git_utils",
    "git_helpers",
    "packages",
    "status_analyzer",
    "utils",
    "stage0",
    "stage1",
    "stage2",
    "stage3",
    "stage4",
    "stage5",
    "stage6",
    "clear",
]