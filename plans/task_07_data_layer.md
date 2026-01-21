# Задача 7: Реализация Data Layer (Smart Sync) ✅ ВЫПОЛНЕНО

## Цель
Обеспечить эффективный доступ к данным (датасетам, изображениям) для всех этапов пайплайна, реализуя стратегию гибридного доступа (ADR-004).

## Статус выполнения
Задача полностью реализована в рамках версии v0.2.0.

### Что было сделано:
1.  **Пакет `packages/data_layer`**:
    *   Создана структура пакета с использованием `uv` и `src` layout.
    *   Определен абстрактный интерфейс `StorageProvider` ([`base.py`](packages/data_layer/src/data_layer/base.py)).
    *   Реализованы провайдеры `LocalStorage` ([`local.py`](packages/data_layer/src/data_layer/local.py)) и `S3Storage` ([`s3.py`](packages/data_layer/src/data_layer/s3.py)).
2.  **Smart Sync Manager**:
    *   Реализован класс `SmartSyncManager` ([`sync.py`](packages/data_layer/src/data_layer/sync.py)), обеспечивающий логику "Sync-before-Run".
    *   Добавлена поддержка загрузки артефактов в удаленное хранилище.
3.  **Конфигурация**:
    *   Внедрены Pydantic-схемы для конфигурации хранилищ ([`schemas/storage.py`](packages/data_layer/src/data_layer/schemas/storage.py)).
    *   Добавлена фабрика для создания провайдеров.
4.  **Тестирование**:
    *   Покрыты тестами основные сценарии работы с локальной ФС и менеджером синхронизации ([`tests/`](packages/data_layer/tests/)).
5.  **Публикация**:
    *   Пакет опубликован как независимый репозиторий: [VLMHyperBenchTeam/data-layer](https://github.com/VLMHyperBenchTeam/data-layer).
    *   Для публикации использован **GitHub MCP Server**.
6.  **Архитектурная очистка**:
    *   Из проекта удалены устаревшие компоненты: папка `docker/` и инструмент `release_tool`.
    *   Корневой `pyproject.toml` очищен от зависимостей плагинов для обеспечения полной изоляции.

## Контекст
См. [ADR-004: Smart Sync](../docs_site/docs/architecture/adr/004-smart-sync.md).

## Подзадачи

1.  [x] **Абстракция Storage Interface**:
    *   Создать пакет `packages/data_layer`.
    *   Определить интерфейс `StorageProvider` (методы `download`, `upload`, `exists`, `list`).
    *   Реализовать провайдеры: `LocalStorage` (прямой доступ к FS) и `S3Storage` (через `boto3`/`minio`).

2.  [x] **Smart Sync Manager**:
    *   Реализовать логику синхронизации "перед запуском" (Sync-before-Run).
    *   Метод `ensure_dataset_available(dataset_name, local_path)`:
        *   Проверяет наличие данных локально.
        *   Если нет — скачивает из S3.
        *   Проверяет целостность (опционально, checksum).

3.  [ ] **Интеграция с Оркестратором**: (Будет выполнено в рамках `task_10_orchestrator_refactor`)
    *   Перед запуском контейнера инференса оркестратор должен вызывать `SmartSyncManager` для подготовки тома с данными.
    *   Монтирование подготовленной локальной директории в Docker-контейнер (`-v /local/cache:/data`).

4.  [x] **Artifact Management**:
    *   Логика загрузки результатов (`answers.csv`, `metrics.csv`, `report.md`) обратно в S3 после завершения этапа.

## Ожидаемый результат
*   [x] Пакет `data_layer`, умеющий прозрачно работать с локальной ФС и S3.
*   [ ] Оркестратор гарантирует наличие данных на диске перед стартом контейнера.
*   [x] Результаты экспериментов надежно сохраняются в объектное хранилище (если настроено).