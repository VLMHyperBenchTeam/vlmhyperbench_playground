# Саммари сессии: Реализация VLMHyperBench v0.2.0 (SNILS Extraction)

**Дата**: 2026-01-22
**Статус**: Инфраструктура реализована, компоненты SNILS готовы, требуется финальная отладка запуска.

## 1. Что реализовано

### Архитектура (Hybrid Host + Containers)
- **Orchestrator Service (Host)**: Python-сервис на хосте (порт 8002). Управляет Docker-контейнерами бенчмарков и GPU. При старте автоматически поднимает инфраструктуру через `docker compose`.
- **Management Plane (Containers)**:
    - **Backend**: FastAPI + SQLModel (SQLite). Хранит эксперименты, общается с Оркестратором.
    - **Redis**: Используется как **Message Broker** (ADR-012) для передачи событий (логи, статусы) от Оркестратора к Бекенду.
    - **Web UI**: React + Vite + Tailwind. Dashboard в стиле VS Code для мониторинга и запуска.

### Задача SNILS Extraction
- **Dataset**: Реализован [`SnilsIterator`](packages/dataset_factory/src/dataset_factory/iterators/snils.py) для загрузки картинок и JSON-разметки из `data/snils`.
- **Metrics**: Реализованы [`StructuralFidelity` и `FieldAccuracy`](packages/metric_registry/src/metric_registry/metrics/structural.py) для оценки качества извлечения данных.
- **Prompt**: Создан [русскоязычный промпт](vlmhyperbench/data_dirs/PromptCollections/snils_extraction/default.json), оптимизированный для модели Qwen2.5-VL.
- **Registries**: Созданы YAML-конфиги в `vlmhyperbench/registries/` (tasks, datasets, metrics, runs).
- **Execution**: Скрипт [`run_vlm.py`](VLMHyperBench/vlmhyperbench/system_dirs/bench_stages/run_vlm.py) адаптирован под новую систему реестров и `PromptManager`.

## 2. Текущее состояние и проблемы

### Проблемы
1. **Orchestrator Not Ready**: Последний запрос к `http://localhost:8002/run` вернул ошибку `"detail":"Orchestrator not ready"`. Это означает, что объект `bootstrapper.orchestrator` в `services/orchestrator_service/src/orchestrator_service/main.py` равен `None`. 
    - *Причина*: Либо `wait_for_healthy` еще не завершился, либо инициализация `AsyncBenchmarkOrchestrator` упала в фоне.
2. **Web UI**: Пользователь сообщил, что контейнер с фронтом "лежит" или показывает стандартную страницу Nginx. Хотя последние правки в `Dockerfile` и `nginx.conf` должны были это исправить.
3. **Backend Docker**: Был исправлен `ImportError` и отсутствие `httpx` путем перехода на сборку через `uv` в `Dockerfile`.

### Конфигурация портов
- **Orchestrator Service**: `http://localhost:8002` (сменили с 8001 из-за конфликтов).
- **Management Backend**: `http://localhost:8000`.
- **Web UI**: `http://localhost:3000`.

## 3. Инструкции для продолжения

1. **Проверить логи Оркестратора**:
   ```bash
   # В терминале где запущен uv run python src/orchestrator_service/main.py
   # Проверить, почему bootstrapper не пометил систему как READY.
   ```
2. **Перезапустить всё**:
   ```bash
   docker compose down
   docker compose up -d --build
   cd services/orchestrator_service && uv run python src/orchestrator_service/main.py
   ```
3. **Проверить Web UI**:
   Убедиться, что `http://localhost:3000` открывает Dashboard и кнопка "New Experiment" работает.
4. **Запустить тест SNILS**:
   Через UI или `curl`:
   ```bash
   curl -X POST http://localhost:8002/run -H "Content-Type: application/json" -d '{"experiment_id": "snils_final_test", "config": {"run_name": "qwen_snils_extraction"}}'
   ```

## 4. Важные файлы
- `services/orchestrator_service/src/orchestrator_service/main.py` — Точка входа системы.
- `docker-compose.yaml` — Описание инфраструктуры.
- `vlmhyperbench/registries/runs/qwen_snils_extraction.yaml` — Конфиг запуска.
- `docs_site/docs/architecture/adr/012-redis-as-message-broker.md` — Описание логики событий.