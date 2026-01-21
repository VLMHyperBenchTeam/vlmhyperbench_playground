# Задача 5: Реализация Management Backend (FastAPI)

## Цель
Создать центральный сервис управления (Management Plane), который будет отвечать за хранение состояния экспериментов, запуск задач оркестратора и предоставление API для фронтенда.

## Контекст
См. [ADR-008: React Dashboard](../docs_site/docs/architecture/adr/008-react-dashboard-with-plotly.md) и [Specification](../docs_site/docs/architecture/specification.md).
Backend должен служить связующим звеном между пользователем (UI) и системой исполнения (Orchestrator).

## Подзадачи

1.  **Базовая структура проекта**:
    *   Создать пакет `packages/management_backend`.
    *   Настроить FastAPI приложение с CORS middleware.
    *   Подключить SQLite (или PostgreSQL) через SQLAlchemy/SQLModel.

2.  **API Эндпоинты**:
    *   `POST /experiments`: Создание нового эксперимента (принимает конфиг JSON/CSV).
    *   `GET /experiments`: Список всех экспериментов.
    *   `GET /experiments/{id}`: Детальная информация и статус.
    *   `GET /analytics/{id}`: Данные для графиков (Plotly JSON).

3.  **Интеграция с Оркестратором**:
    *   Реализовать фоновый запуск `BenchmarkOrchestrator` при создании эксперимента.
    *   Настроить механизм отслеживания статуса процессов (PID, Return Code).

4.  **WebSockets (Real-time updates)**:
    *   Реализовать WebSocket эндпоинт `/ws/{experiment_id}`.
    *   Подключить `EventBus` оркестратора к отправке сообщений в WS канал (лога, прогресс-бары).

## Ожидаемый результат
*   Запущенный сервис на порту 8000.
*   Swagger UI доступен по `/docs`.
*   Можно создать эксперимент через API и получать обновления статуса в реальном времени.