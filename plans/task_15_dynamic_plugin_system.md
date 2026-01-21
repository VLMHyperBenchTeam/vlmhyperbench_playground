# Задача 15: Упрощенная Система Плагинов (Package-based Extensions)

## Цель
Позволить пользователям расширять функциональность (датасеты, метрики, бэкенды) путем создания обычных Python-пакетов и указания их в конфигурации.

## Контекст
Вместо сложной системы `entry_points` и автообнаружения, мы будем использовать явную конфигурацию. Пользователь реализует нужный интерфейс в своем пакете, указывает этот пакет в конфиге `MLTask` или `RunTask`, и система автоматически устанавливает его в контейнер.

## Реализация

1.  **Конфигурация (YAML)**:
    В `MLTask` или `RunTask` добавляется секция `custom_packages`:
    ```yaml
    custom_packages:
      - name: "my_custom_dataset"
        source: "git+https://github.com/user/repo.git"
        # Или локальный путь (будет смонтирован)
        # source: "/local/path/to/package"
    
    dataset:
      type: "my_custom_dataset.MyIterator" # Полный путь к классу
    ```

2.  **Dependency Injector Update**:
    *   Оркестратор читает список `custom_packages`.
    *   Если `source` — это URL/PyPI, добавляет в команду `pip install`.
    *   Если `source` — локальный путь, монтирует его в `/tmp/packages` и делает `pip install /tmp/packages/...`.

3.  **Dynamic Import**:
    *   В коде (`IteratorFabric`, `MetricRegistry`) вместо жестких импортов использовать `importlib.import_module`.
    *   Если пользователь указал `type: "my_pkg.MyClass"`, фабрика делает:
        ```python
        module_name, class_name = type_str.rsplit(".", 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return cls(...)
        ```

## Ожидаемый результат ✅ ВЫПОЛНЕНО
*   Максимальная простота для пользователя: "Написал пакет -> Указал в конфиге -> Работает".
*   Никакой магии с entry points.
*   Полная поддержка кастомных датасетов, метрик и даже моделей.

## Реализация
1. Созданы пакеты `packages/metric_registry` и `packages/dataset_factory`.
2. Реализована поддержка динамического импорта классов через `importlib` по полному пути (dot notation).
3. Интегрировано в базовые фабрики и реестры.