# HPM Technical Design: Manifests & Runtime Logic

Этот документ детализирует структуру манифестов и логику работы рантайма HPM (HyperPackageManager) для поддержки сценариев Prod (Qwen) и Dev (DeepSeek).

## 1. Структура Манифестов (Manifest Definitions)

Манифесты (`hpm.yaml`) являются единым источником правды для определения пакетов.

### 1.1. Базовый шаблон (Schema)

```yaml
name: str              # Уникальное имя пакета
version: str           # Версия (SemVer)
description: str       # Описание
type: str              # Тип пакета: "library", "service", "virtual" (default: library)

# Источники кода для разных режимов
sources:
  prod:
    type: "git" | "pypi"
    url: str           # URL репозитория или имя в PyPI
    ref: str           # Tag, Branch или Commit SHA (для git)
  dev:
    type: "local"
    path: str          # Относительный путь (для монорепозитория) или placeholder
    editable: bool     # Устанавливать ли в режиме -e

# Зависимости (абстрактные или конкретные)
dependencies:
  - "numpy>=1.20"
  - "torch==2.1.2"
  - name: "api_wrapper" # Другой HPM пакет
    version: "^0.1.0"

# Точки входа (для запускаемых сервисов)
entrypoints:
  serve: "python -m module.path.serve"
  test: "pytest tests/"
```

### 1.2. Типы Пакетов (Package Types)

*   **library**: Обычная Python библиотека. Используется как зависимость для других пакетов.
*   **service**: Пакет, содержащий исполняемый код (сервер, воркер) и определяющий `entrypoints`. Может быть запущен через `hpm run`.
*   **virtual**: Абстрактный пакет, определяющий интерфейс (например, `inference-backend`). HPM разрешает его в конкретную реализацию (например, `vllm-backend` или `sglang-backend`) на этапе разрешения зависимостей.

### 1.3. Адаптеры Инференса (Inference Framework Adapters)

VLMHyperBench поддерживает различные бэкенды инференса через систему адаптеров. Эти адаптеры упаковываются как HPM пакеты (обычно типа `service` или `library` с entrypoints):

*   **vLLM Adapter**: Высокопроизводительный инференс (основной для продакшена).
*   **SGLang Adapter**: Для сложных сценариев структурированной генерации.
*   **Hugging Face Adapter**: Референсная реализация через `transformers` (для отладки и бейзлайнов).

### 1.4. Сценарий 1: Qwen2-VL Adapter (Production)

Этот пакет оборачивает модель Qwen2-VL. В проде мы хотим фиксированную версию из Git.

**File:** `packages/vlm-adapter-qwen/hpm.yaml`

```yaml
name: "vlm-adapter-qwen"
version: "0.2.0"
type: "service"
description: "Adapter for Qwen2-VL models using vLLM backend"

sources:
  prod:
    type: "git"
    url: "https://github.com/vlmhyperbench/vlm-adapters.git"
    ref: "tags/v0.2.0"
    subdirectory: "qwen"
  dev:
    type: "local"
    path: "../../packages/vlm-adapter-qwen"
    editable: true

dependencies:
  - "vllm>=0.6.0"
  - name: "api_wrapper"
    version: "*"

entrypoints:
  serve: "python -m vlm_adapter_qwen.serve --host 0.0.0.0 --port 8000"
```

### 1.5. Сценарий 2: DeepSeek-OCR Adapter (Development)

Разработчик пишет кастомную логику для DeepSeek. Он хочет монтировать локальный код.

**File:** `packages/deepseek-adapter/hpm.yaml`

```yaml
name: "deepseek-adapter"
version: "0.1.0-dev"
type: "service"
description: "Custom adapter for DeepSeek-OCR with specific prompting"

sources:
  prod:
    type: "git"
    url: "https://github.com/vlmhyperbench/deepseek-adapter.git"
    ref: "main"
  dev:
    type: "local"
    path: "."
    editable: true

dependencies:
  - "openai>=1.0.0"
  - name: "api_wrapper"
    version: "*"

entrypoints:
  serve: "python -m deepseek_adapter.main --port 8002"
```

## 2. HPM Runtime Logic

`hpm` — это универсальный инструмент управления окружением, который работает в двух основных контекстах:

1.  **CLI Utility**: Используется разработчиком или CI/CD для управления зависимостями, генерации lock-файлов и локального запуска.
2.  **Container Entrypoint**: Работает как процесс PID 1 внутри Docker-контейнера, отвечая за JIT-инициализацию окружения перед запуском основного приложения.

### 2.1. Команды CLI

1.  **`hpm lock`**: Разрешает зависимости и генерирует lock-файл.
    *   Args: `--plugins <list>`, `--mode <prod|dev>`
    *   Output: JSON/TOML контент (stdout), который можно закодировать в base64.
2.  **`hpm install`**: Устанавливает зависимости.
    *   Input: `uv.lock` (файл) или `HPM_LOCK_B64` (env).
3.  **`hpm run`**: Выполняет команду в окружении.
    *   Args: `--entrypoint <name>` OR `-- <command>`

### 2.2. Bootstrapping Flow (Внутри контейнера)

Когда контейнер запускается с `ENTRYPOINT ["hpm"]`, выполняется следующая логика (псевдокод на Python):

```python
import os
import sys
import subprocess
import base64
from pathlib import Path

def main():
    # 1. Environment Setup
    run_mode = os.getenv("RUN_MODE", "prod")
    lock_b64 = os.getenv("HPM_LOCK_B64")
    dev_overlay = json.loads(os.getenv("HPM_DEV_OVERLAY", "{}"))

    # 2. Dependency Resolution / Restoration
    if lock_b64:
        # PROD PATH: Восстановление из Lock-файла
        print("[HPM] Restoring environment from HPM_LOCK_B64...")
        lock_content = base64.b64decode(lock_b64).decode('utf-8')
        Path("uv.lock").write_text(lock_content)
        
        # Sync using uv
        subprocess.run(["uv", "sync", "--frozen"], check=True)
        
    elif run_mode == "dev":
        # DEV PATH: Динамическая установка локальных пакетов
        print("[HPM] Dev mode detected. Installing from overlays...")
        for pkg_name, pkg_path in dev_overlay.items():
            print(f"[HPM] Installing editable: {pkg_name} -> {pkg_path}")
            # Используем uv pip install -e
            subprocess.run(["uv", "pip", "install", "-e", pkg_path, "--system"], check=True)
            
    # 3. Command Execution
    args = sys.argv[1:]
    if args[0] == "run":
        # Parse 'run' arguments
        # ... logic to extract --entrypoint or raw command ...
        
        if entrypoint_name:
            # Найти команду в манифесте (требует наличия манифеста в контексте или передаче его)
            # В упрощенной схеме, если мы в контейнере плагина, манифест лежит рядом.
            cmd = resolve_entrypoint(entrypoint_name)
        else:
            cmd = args_after_double_dash # то что после --
            
        print(f"[HPM] Executing: {cmd}")
        os.execvp(cmd[0], cmd)
```

### 2.3. Integration with `uv`

Мы используем `uv` как бэкенд для установки.
*   **Prod:** `uv sync` обеспечивает детерминированную установку версий.
*   **Dev:** `uv pip install -e .` позволяет редактировать код на хосте и видеть изменения в контейнере (через volume mount).

### 2.4. Обработка `HPM_DEV_OVERLAY`

Переменная `HPM_DEV_OVERLAY` — это JSON map: `{"package_name": "/container/path/to/source"}`.
Она говорит HPM: "Не качай этот пакет из Git/PyPI, а возьми его по этому локальному пути и поставь в editable режиме".

Это ключевой механизм для локальной разработки адаптеров без пересборки образов.