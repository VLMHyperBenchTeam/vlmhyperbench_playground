# Задача 14: Рефакторинг Dataset Iterator ✅ ВЫПОЛНЕНО

## Цель
Обеспечить поддержку расширяемости датасетов. Пользователь должен иметь возможность легко добавить поддержку своего формата датасета, создав новый класс итератора.

## Контекст
Текущая реализация `dataset_iterator` была жестко привязана к определенным форматам. Мы перешли к модели `dataset_factory`, где `RunTask` или `MLTask` могут указывать тип датасета, а система динамически подгружает нужный итератор.

## Выполненные подзадачи

1.  **Dataset Interface** ✅:
    *   Определен абстрактный базовый класс [`DatasetIterator`](packages/dataset_factory/src/dataset_factory/interfaces.py:5).
    *   Реализованы обязательные методы: `__iter__`, `__len__`, `get_item(idx)`.
    *   Создана унифицированная Pydantic модель [`DatasetItem`](packages/dataset_factory/src/dataset_factory/models.py:4) (image_path, text, metadata).

2.  **Dataset Registry** ✅:
    *   Создан реестр итераторов [`DatasetRegistry`](packages/dataset_factory/src/dataset_factory/registry.py:4).
    *   Реализован декоратор `@DatasetRegistry.register(name)` для автоматической регистрации классов.

3.  **Dataset Factory** ✅:
    *   Реализована [`DatasetFactory`](packages/dataset_factory/src/dataset_factory/factory.py:6), которая заменяет старые фабрики и поддерживает создание итераторов как из реестра, так и через динамический импорт.

4.  **Custom Dataset Support** ✅:
    *   Добавлена поддержка динамической загрузки модулей. Пользователь может указать полный путь к классу (например, `my_package.MyIterator`), и фабрика загрузит его JIT.
    *   Все компоненты вынесены в отдельный пакет [`packages/dataset_factory`](packages/dataset_factory).

## Результаты
*   **Плагинная архитектура**: Пакет `dataset_factory` полностью автономен и поддерживает расширение без изменения кода ядра.
*   **Unit-тесты**: Реализовано полное покрытие тестами в [`tests/test_factory.py`](packages/dataset_factory/tests/test_factory.py).
*   **Публикация**: Пакет опубликован в GitHub организации [VLMHyperBenchTeam/dataset_factory](https://github.com/VLMHyperBenchTeam/dataset_factory).
*   **Стандартизация**: Сборка настроена через `uv_build` в [`pyproject.toml`](packages/dataset_factory/pyproject.toml).