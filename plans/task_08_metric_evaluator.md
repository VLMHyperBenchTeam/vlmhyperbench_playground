# Задача 8: Реализация Metric Evaluator & Registry

## Цель
Обеспечить гибкую систему расчета метрик с поддержкой версионирования алгоритмов и валидации структуры ответов (Pydantic).

## Контекст
См. [ADR-007: Structured Output Validation](../docs_site/docs/architecture/adr/007-structured-output-validation.md) и [Concept](../docs_site/docs/architecture/concept.md).
Метрики должны быть отделены от логики инференса и поддерживать расширение (плагинная архитектура).

## Подзадачи

1.  **Metric Registry**:
    *   Создать реестр метрик в `packages/bench_utils`.
    *   Реализовать декоратор `@register_metric(name, version)` для автоматической регистрации функций расчета.
    *   Поддержать версионирование (например, `ANLS_v1` vs `ANLS_v2`).

2.  **Structural Fidelity & Validation**:
    *   Интегрировать `pydantic` для валидации JSON-ответов.
    *   Реализовать метрику `StructuralFidelity` (1/0), проверяющую соответствие ответа заданной JSON Schema.
    *   Если валидация не прошла -> остальные метрики для этого объекта не считаются (или помечаются как invalid).

3.  **Refactor MetricEvaluator**:
    *   Обновить класс `MetricEvaluator` для использования реестра.
    *   Реализовать стратегии агрегации: `by_id` (детально), `by_category` (группировка), `general` (общий итог).

4.  **Новые метрики**:
    *   Добавить метрики производительности (Resource Metrics): Latency, TTFT, Peak Memory (получаемые из логов инференса).

## Ожидаемый результат
*   Пакет `bench_utils` поддерживает регистрацию новых метрик.
*   Валидация JSON через Pydantic работает и влияет на метрику `StructuralFidelity`.
*   Отчеты содержат как текстовые метрики (CER/ANLS), так и метрики стабильности формата и производительности.