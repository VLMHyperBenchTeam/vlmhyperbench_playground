# Задача 11: Реализация Реестра Задач (RunTask & MLTask)

## Цель
Разделить конфигурацию запуска на два уровня (MLTask и RunTask) и обеспечить возможность группировки запусков в Планы Экспериментов.

## Контекст
Мы хотим, чтобы Оркестратор мог запускать самые разные задачи (VQA, OCR, Classification), не зная заранее деталей реализации каждой из них.
Исследования показывают, что популярные инструменты (MLFlow, DVC) используют реестры для версионирования моделей и экспериментов. Мы применим этот подход к **типам задач**.

## Структура Реестров (YAML)

### 1. MLTask Registry (`vlmhyperbench/configs/ml_tasks/`)
Шаблоны типов задач. Определяют зависимости и скрипты.
Пример `vqa.yaml`:
```yaml
name: VQA
entry_point: "vlmhyperbench.tasks.vqa" # Python module path
required_packages: ["pillow", "torch"]
supported_metrics: ["anls", "cer"]
```

**Важно**: Вместо копирования скриптов `run_vqa.py`, мы упакуем логику задач в пакеты (например, `packages/tasks/vqa`). `entry_point` будет указывать на модуль, который можно запустить через `python -m`.

### 2. RunTask Registry (`vlmhyperbench/configs/run_tasks/`)
Атомарные единицы работы. Описывают **одну** комбинацию "Модель + Датасет".
Пример `qwen_vqa.yaml`:
```yaml
name: "qwen_docvqa_ru"
ml_task: "VQA"
model: {name: "Qwen2-VL", framework: "vllm"}
dataset: "docvqa_ru"
metrics: ["anls"]
```

### 3. Experiment Plan (`vlmhyperbench/configs/experiments/`)
Файл, который скармливается Оркестратору. Содержит список RunTask'ов.
Пример `benchmark_2025.yaml`:
```yaml
name: "Grand VLM Benchmark 2025"
parallelism: 4
tasks:
  - "qwen_docvqa_ru"
  - "llava_docvqa_ru"
```

## Подзадачи

1.  **MLTask Registry Module**:
    *   Создать пакет `packages/task_registry`.
    *   Реализовать класс `MLTaskRegistry`, который сканирует `vlmhyperbench/configs/ml_tasks/*.yaml`.

2.  **Task Implementation Packages**:
    *   Создать `packages/tasks/` и подпакеты для каждой задачи (`vqa`, `ocr`, `classification`).
    *   Каждый пакет должен иметь `__main__.py` для запуска.

3.  **Experiment Plan Loader**:
    *   Реализовать парсинг плана эксперимента и разрешение ссылок на RunTask'и.

4.  **Orchestrator Integration**:
    *   Оркестратор устанавливает пакет задачи (`pip install packages/tasks/vqa`) в контейнер.
    *   Запускает задачу через `python -m vlmhyperbench.tasks.vqa`.

5.  **CLI & Web UI**:
    *   Команды для запуска и редактирования планов.
    *   Интеграция с редактором кода в браузере.

## Ожидаемый результат
*   Модульная структура задач: код задач отделен от ядра.
*   Легкое добавление новых типов задач (новый пакет + YAML конфиг).
*   Гибкое управление экспериментами через YAML планы.