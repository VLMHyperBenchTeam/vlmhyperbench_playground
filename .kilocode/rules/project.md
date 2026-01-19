# Memory Bank: VLMHyperBench

## Обзор проекта
VLMHyperBench — это open-source фреймворк для оценки возможностей Vision Language Models (VLM), с акцентом на распознавание документов (включая русский язык). Инструмент позволяет исследователям и инженерам сравнивать модели, запускаемые на различных фреймворках (Hugging Face, vLLM, SGLang), в изолированных окружениях.

## Архитектура
Система построена на модульной архитектуре, где каждый этап (инференс модели, оценка метрик) выполняется в изолированном Docker-контейнере.

### Основные сущности и компоненты

#### 1. Orchestrator (`BenchmarkOrchestrator`)
*   **Локация**: `VLMHyperBench/benchmark_scheduler/benchmark_orchestrator.py`
*   **Функции**:
    *   Центральный управляющий элемент.
    *   Считывает глобальную конфигурацию и список задач.
    *   Проверяет и скачивает необходимые Docker-образы.
    *   Запускает контейнеры для этапов инференса и оценки, монтируя необходимые директории (volumes).

#### 2. Configuration Management
*   **User Config**: Пользователь задает задачи в CSV файле (например, `user_config_model_eval.csv`), указывая датасет, модель, промпты и метрики.
*   **VLM Base**: Реестр моделей (`vlmhyperbench/vlm_base.csv`) хранит технические детали: имя Docker-образа, python-пакеты и классы для инициализации конкретной модели.
*   **UserConfigReader**: Класс (`VLMHyperBench/benchmark_scheduler/user_config_reader.py`), объединяющий пользовательский конфиг с базой VLM для создания полных конфигураций запуска (`BenchmarkRunConfig`).

#### 3. Этапы выполнения (Stages)
Скрипты этапов находятся в `VLMHyperBench/vlmhyperbench/system_dirs/bench_stages/` и монтируются в контейнеры.

*   **Stage: Run VLM (Инференс)**
    *   **Скрипт**: `run_vlm.py`
    *   **Описание**: Запускается внутри контейнера с GPU. Инициализирует модель через `ModelFactory`, создает итератор по датасету (`IteratorFabric`) и сохраняет ответы модели.
*   **Stage: Eval Metrics (Оценка)**
    *   **Скрипт**: `run_eval.py` (подразумевается архитектурой)
    *   **Описание**: Запускается внутри легковесного контейнера (`metric-evaluator`). Сравнивает ответы модели с эталонными значениями (Ground Truth) и считает метрики.

## Структура директорий (VLMHyperBench)

*   `benchmark_scheduler/` — Логика планирования и управления Docker-контейнерами.
*   `vlmhyperbench/`
    *   `data_dirs/` — Хранилище данных (датасеты, промпты, ответы моделей, отчеты).
    *   `system_dirs/` — Системные ресурсы, пробрасываемые в контейнеры:
        *   `bench_stages/` — Скрипты исполнения (`run_vlm.py`).
        *   `cfg/` — Конфигурационные файлы (`VLMHyperBench_config.json`, requirements).
    *   `vlm_base.csv` — База данных поддерживаемых моделей.
*   `run_benchmark.py` — Точка входа (Entry point) приложения.

## Технологический стек
*   **Язык**: Python 3.10+
*   **Инфраструктура**: Docker (управление через `docker-py`).
*   **Данные**: Pandas (работа с CSV конфигами и отчетами).
*   **Внутренние зависимости**:
    *   `benchmark-run-config` — Управление конфигурациями запусков.
    *   `config-manager` — Управление путями и настройками.

## Поток данных (Data Flow)
1.  Пользователь заполняет `user_config.csv`.
2.  `run_benchmark.py` запускает `BenchmarkOrchestrator`.
3.  Оркестратор формирует список задач (`BenchmarkRunConfig`).
4.  **Loop по задачам**:
    *   Запуск Docker-контейнера модели -> Монтирование данных -> `run_vlm.py` -> Генерация ответов (CSV).
    *   Запуск Docker-контейнера оценки -> Монтирование ответов -> `run_eval.py` -> Расчет метрик (CSV).

## Документация и Решения (ADR)
Ключевые архитектурные решения и концепции задокументированы в папке `docs/docs_new/`:

*   **Архитектурная концепция**: [`docs/docs_new/01_architecture_concept.md`](docs/docs_new/01_architecture_concept.md) — Основной документ, описывающий модульную архитектуру, изоляцию и взаимодействие компонентов.
*   **Architecture Decision Records (ADR)**: [`docs/docs_new/09_architecture_decision_records.md`](docs/docs_new/09_architecture_decision_records.md) — Фиксация важных технических решений (изоляция, динамические зависимости, API wrapper).
*   **Сравнительный анализ**: [`docs/docs_new/10_comparative_analysis.md`](docs/docs_new/10_comparative_analysis.md) — Сравнение с EvalScope и другими фреймворками.
