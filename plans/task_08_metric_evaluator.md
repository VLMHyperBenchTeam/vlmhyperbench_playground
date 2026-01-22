# Задача 8: Реализация Metric Evaluator & Registry ✅ ВЫПОЛНЕНО

## Цель
Обеспечить гибкую систему расчета метрик с поддержкой версионирования алгоритмов и валидации структуры ответов (Pydantic).

## Что сделано
1.  **Metric Registry**: Реализован динамический реестр с поддержкой Namespaces (Backends), версионирования и декоратором `@register_metric`.
2.  **Base Classes**: Созданы `BaseMetric` и `MetricResult` (Pydantic) для стандартизации вывода.
3.  **Structural Fidelity**: Реализована валидация JSON через Pydantic v2.
4.  **Metric Evaluator**: Создан оркестратор с поддержкой фильтрации по бэкендам для обеспечения изоляции зависимостей.
5.  **Resource Metrics**: Добавлены метрики Latency и Peak Memory.
6.  **Backend Isolation**: Реализована стратегия многоэтапной оценки в изолированных контейнерах.
7.  **Tests**: Пакет полностью покрыт unit-тестами.

## Контекст
См. [ADR-007: Structured Output Validation](../docs_site/docs/architecture/adr/007-structured-output-validation.md) и [Concept](../docs_site/docs/architecture/concept.md).
Метрики должны быть отделены от логики инференса и поддерживать расширение (плагинная архитектура).

## Подзадачи

1.  **Metric Registry** [x]:
    *   Создан реестр метрик в пакете `metric_registry`.
    *   Реализован декоратор `@register_metric(name, version, backend)` для автоматической регистрации.
    *   Поддерживается иерархическая структура `{name: {backend: {version: cls}}}`.
    *   Добавлен механизм регистрации метаданных бэкенда (`register_backend`).

2.  **Structural Fidelity & Validation** [x]:
    *   Интегрирован `pydantic v2` для валидации структурированных JSON-ответов.
    *   Реализована метрика `StructuralFidelityMetric` (1.0/0.0).
    *   Описание ошибок валидации сохраняется в метаданных результата.

3.  **MetricEvaluator** [x]:
    *   Создан новый класс `MetricEvaluator`, поддерживающий параметр `active_backend`.
    *   Реализована логика фильтрации метрик для обеспечения изоляции зависимостей.
    *   Добавлена базовая агрегация через `pandas`.

4.  **Новые метрики** [x]:
    *   Добавлены метрики производительности: `LatencyMetric` и `PeakMemoryMetric`.

## Ожидаемый результат
*   Пакет `metric_registry` поддерживает регистрацию новых метрик.
*   Валидация JSON через Pydantic работает и влияет на метрику `StructuralFidelity`.
*   Отчеты содержат как текстовые метрики (CER/ANLS), так и метрики стабильности формата и производительности.