# Контекст: Создание отдельного PlantUML Docker рендерера

## Описание задачи

Необходимо выделить созданный PlantUML Docker рендерер в отдельный GitHub репозиторий как самостоятельный инструмент, аналогично существующему `release_tool`.

## Текущее состояние

### Что уже создано:
- ✅ Dockerfile для рендеринга PlantUML диаграмм (`docker/Dockerfile-plantuml`)
- ✅ Python скрипт для пакетного рендеринга (`docker/render_plantuml.py`)
- ✅ Документация по использованию (`docs/plantuml-docker-renderer.md`)
- ✅ Все изменения зафиксированы в git коммитах

### Функциональность рендерера:
- Автоматический поиск всех `.puml` файлов в указанной директории
- Рендеринг в форматы SVG и PNG
- Настраиваемая точка монтирования через переменную `MOUNT_POINT`
- Подробное логирование процесса
- Обработка ошибок

## Цель

Создать отдельный GitHub репозиторий `VLMHyperBenchTeam/plantuml-docker-renderer` и интегрировать его в основной проект как git submodule.

## Архитектура проекта

### Основной проект использует:
- Git submodules для инструментов (см. `.gitmodules`)
- GitHub Container Registry для Docker образов (`ghcr.io/vlmhyperbenchteam/`)
- Open source подход с публичными репозиториями

### Примеры существующих инструментов:
- `release_tool` - инструмент для создания релизов
- `packages/*` - различные Python пакеты

## Требования к новому репозиторию

### Структура:
```
plantuml-docker-renderer/
├── Dockerfile
├── render_plantuml.py
├── README.md
├── examples/
│   ├── sample.puml
│   └── README.md
├── .github/workflows/docker-publish.yml
├── .gitignore
└── LICENSE
```

### Docker образ:
- Registry: `ghcr.io/vlmhyperbenchteam/plantuml-renderer`
- Базовый образ: `plantuml/plantuml:latest`
- Поддержка форматов: SVG, PNG

## Интеграция в основной проект

### Добавить в .gitmodules:
```
[submodule "tools/plantuml-renderer"]
    path = tools/plantuml-renderer
    url = https://github.com/VLMHyperBenchTeam/plantuml-docker-renderer.git
```

### Обновить документацию:
- Ссылки на использование образа из GitHub Container Registry
- Примеры команд с новым образом

## Критерии готовности

- [x] Создан GitHub репозиторий `VLMHyperBenchTeam/plantuml-docker-renderer`
- [x] Перенесены все файлы из основного проекта
- [ ] Добавлен submodule в основной проект
- [ ] Обновлена документация в основном проекте
- [ ] Протестирована работа с образом из GitHub Container Registry

## Команды для тестирования

```bash
# Использование локального образа
export MOUNT_POINT="/workspace"
docker run --rm -v $(pwd):$MOUNT_POINT plantuml-renderer $MOUNT_POINT/docs/architecture/diagrams svg

# Использование образа из GitHub Container Registry (после публикации)
export MOUNT_POINT="/workspace"
docker run --rm -v $(pwd):$MOUNT_POINT ghcr.io/vlmhyperbenchteam/plantuml-renderer:latest $MOUNT_POINT/docs/architecture/diagrams svg
```

## Дополнительные требования

- Сохранить всю функциональность существующего рендерера
- Обеспечить обратную совместимость
- Добавить примеры использования
- Создать подробную документацию
- Настроить автоматическое тестирование