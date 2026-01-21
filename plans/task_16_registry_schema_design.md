# Задача 16: Проектирование Схем Реестров (Configuration Schemas)

## Цель
Разработать детальные схемы (Pydantic Models / JSON Schema) для всех типов реестров и конфигурационных файлов, обеспечивая связность и валидацию данных.

## Концепция
`MLTask` определяет "интерфейс" задачи (какие данные нужны, какие метрики применимы). `RunTask` — это конкретная реализация (какой датасет взять, какую модель запустить).

## 1. MLTask Schema (`ml_task.yaml`)
Описывает тип задачи.
```yaml
name: "VQA"
description: "Visual Question Answering"
version: "1.0.0"

# Требования к окружению
environment:
  entry_point: "vlmhyperbench.tasks.vqa" # Python module
  default_packages: ["pillow", "torch"]

# Интерфейс данных (для валидации датасета)
dataset_interface:
  type: "image_text_pair" # Ссылка на схему данных
  required_fields: ["image_path", "question", "answer"]

# Доступные метрики (ссылки на Metric Registry)
supported_metrics:
  - "anls"
  - "cer"
  - "bleu"

# Доступные форматы отчетов
supported_reports:
  - "vqa_summary"
  - "vqa_detailed"
```

## 2. Dataset Schema (`dataset.yaml`)
Описывает конкретный датасет.
```yaml
name: "docvqa_ru"
type: "vlmhyperbench.datasets.DocVQA" # Класс итератора
path: "s3://datasets/docvqa_ru" # Или локальный путь
split: "test"
# Специфичные параметры для итератора
params:
  image_dir: "images/"
  annotation_file: "val_v1.0.json"
```

## 3. RunTask Schema (`run_task.yaml`)
Описывает единичный запуск.
```yaml
name: "qwen_docvqa_run_01"
ml_task: "VQA" # Ссылка на MLTask

model:
  name: "Qwen2-VL-7B"
  framework: "vllm"
  docker_image: "vlmhyperbench/vlm-base-hf:latest"
  # Параметры инференса
  params:
    temperature: 0.2
    max_tokens: 1024

dataset: "docvqa_ru" # Ссылка на Dataset Schema (или inline определение)

metrics:
  - "anls" # Должны быть в supported_metrics MLTask'а

# Плагины (опционально)
custom_packages:
  - name: "my_custom_metric"
    source: "./my_metrics"
```

## 4. Experiment Plan Schema (`experiment.yaml`)
Группирует RunTasks.
```yaml
name: "Benchmark 2025"
parallelism: 4
tasks:
  - "run_tasks/qwen_docvqa.yaml"
  - "run_tasks/llava_docvqa.yaml"
  # Inline definition
  - name: "custom_run"
    ml_task: "VQA"
    ...
```

## Подзадачи
1.  Создать Pydantic модели для каждой схемы в `packages/task_registry/schemas.py`.
2.  Реализовать валидацию перекрестных ссылок (например, что метрика в RunTask разрешена в MLTask).
3.  Написать тесты для валидатора.

## Ожидаемый результат
*   Строгая типизация конфигураций.
*   Понятные сообщения об ошибках при неверном конфиге.
*   Автогенерация документации по полям конфига.