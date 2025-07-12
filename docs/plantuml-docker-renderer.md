# PlantUML Docker Renderer

Данный документ описывает использование Docker образа для автоматического рендеринга PlantUML диаграмм в SVG формат.

## Описание

Docker образ `plantuml-renderer` основан на официальном образе [plantuml/plantuml](https://hub.docker.com/r/plantuml/plantuml) и предназначен для пакетного рендеринга всех PlantUML файлов (`.puml`) в указанной директории в SVG формат.

## Сборка образа

```bash
# Перейдите в директорию docker
cd docker

# Соберите образ
docker build -f Dockerfile-plantuml -t plantuml-renderer .
```

## Использование

### Базовое использование

```bash
# Установить точку монтирования (по умолчанию /workspace)
export MOUNT_POINT="/workspace"

# Рендеринг всех .puml файлов в SVG
docker run --rm -v $(pwd):$MOUNT_POINT plantuml-renderer $MOUNT_POINT/docs/architecture/diagrams svg

# Рендеринг всех .puml файлов в PNG
docker run --rm -v $(pwd):$MOUNT_POINT plantuml-renderer $MOUNT_POINT/docs/architecture/diagrams png
```

### Примеры использования

#### 1. Рендеринг диаграмм в текущем проекте

```bash
# Из корня проекта
export MOUNT_POINT="/workspace"
docker run --rm -v $(pwd):$MOUNT_POINT plantuml-renderer $MOUNT_POINT/docs/architecture/diagrams svg
```

#### 2. Рендеринг диаграмм в произвольной папке

```bash
# Рендеринг диаграмм в папке /path/to/diagrams
export MOUNT_POINT="/repo"
docker run --rm -v /path/to/diagrams:$MOUNT_POINT plantuml-renderer $MOUNT_POINT png
```

#### 3. Рендеринг с выводом в отдельную папку

```bash
# Монтируем исходную папку и папку для результатов
export MOUNT_POINT="/workspace"
docker run --rm \
  -v $(pwd)/docs/architecture/diagrams:$MOUNT_POINT/source \
  -v $(pwd)/output/svg:$MOUNT_POINT/output \
  plantuml-renderer $MOUNT_POINT/source svg
```

## Структура образа

### Основные компоненты

- **Базовый образ**: `plantuml/plantuml:latest`
- **Дополнительные пакеты**: bash, findutils, grep
- **Скрипт рендеринга**: `/usr/local/bin/render-plantuml`

### Алгоритм работы

1. Проверка наличия аргумента с путем к папке
2. Валидация существования указанной директории
3. Поиск всех файлов с расширением `.puml`
4. Последовательный рендеринг каждого файла в SVG
5. Проверка успешности создания SVG файлов
6. Вывод результатов обработки

## Возможности

### Поддерживаемые форматы

- **Входные файлы**: `.puml` (PlantUML)
- **Выходные файлы**: `.svg` (Scalable Vector Graphics)

### Особенности

- **Автоматический поиск**: Находит все `.puml` файлы в указанной директории
- **Сохранение структуры**: SVG файлы создаются в тех же папках, что и исходные `.puml` файлы
- **Обработка ошибок**: Выводит информацию об успешных и неудачных операциях
- **Безопасность**: Использует официальный PlantUML образ

## Интеграция с CI/CD

### GitHub Actions

```yaml
name: Render PlantUML Diagrams

on:
  push:
    paths:
      - 'docs/**/*.puml'
  pull_request:
    paths:
      - 'docs/**/*.puml'

jobs:
  render-plantuml:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build PlantUML renderer
        run: |
          cd docker
          docker build -f Dockerfile-plantuml -t plantuml-renderer .

      - name: Render PlantUML diagrams
        run: |
          docker run --rm -v $(pwd):/workspace plantuml-renderer /workspace/docs/architecture/diagrams

      - name: Commit rendered SVGs
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add docs/**/*.svg
          git commit -m "Auto-render PlantUML diagrams" || exit 0
          git push
```

### GitLab CI

```yaml
render-plantuml:
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker build -f docker/Dockerfile-plantuml -t plantuml-renderer ./docker
  script:
    - docker run --rm -v $(pwd):/workspace plantuml-renderer /workspace/docs/architecture/diagrams
  only:
    changes:
      - docs/**/*.puml
```

## Устранение неполадок

### Частые проблемы

#### 1. Ошибка "Директория не существует"

```bash
# Убедитесь, что путь указан правильно
docker run --rm -v $(pwd):/workspace plantuml-renderer /workspace/correct/path/to/diagrams
```

#### 2. Файлы не рендерятся

```bash
# Проверьте синтаксис PlantUML файлов
# Убедитесь, что файлы имеют расширение .puml
```

#### 3. Проблемы с правами доступа

```bash
# Запустите с правами текущего пользователя
docker run --rm -v $(pwd):/workspace -u $(id -u):$(id -g) plantuml-renderer /workspace/docs/architecture/diagrams
```

### Отладка

```bash
# Запуск в интерактивном режиме
docker run --rm -it -v $(pwd):/workspace plantuml-renderer /bin/bash

# Проверка содержимого скрипта
cat /usr/local/bin/render-plantuml
```

## Ссылки

- [Официальный PlantUML Docker образ](https://hub.docker.com/r/plantuml/plantuml)
- [PlantUML документация](https://plantuml.com/)
- [PlantUML синтаксис](https://plantuml.com/guide)
- [SVG формат](https://www.w3.org/Graphics/SVG/)

## Лицензия

Данный образ использует официальный PlantUML образ, который распространяется под лицензией GPL v3.