# Проблема с перемещением Git подмодулей

## Описание проблемы

При попытке переместить Git подмодули в новую директорию и обновить пути в файле `.gitmodules`, могут возникнуть проблемы с отслеживанием подмодулей. Git продолжает искать подмодули по старым путям, даже после обновления конфигурации.

Пример ошибки:
```
fatal: No url found for submodule path 'plantuml-docker-renderer' in .gitmodules
```

## Причина возникновения

Проблема возникает из-за того, что Git хранит информацию о подмодулях в нескольких местах:
1. Файл `.gitmodules` - основная конфигурация
2. Индекс Git (staging area) - кэшированные пути
3. Внутренняя база данных Git в `.git/config`

Когда подмодуль перемещается, информация в индексе и внутренней базе данных может остаться неактуальной, что приводит к конфликту между новыми путями в `.gitmodules` и старыми путями в кэше Git.

## Решение

### Шаг 1: Обновление конфигурации

Обновите файл `.gitmodules`, изменив пути подмодулей на новые:

```ini
[submodule "tools/plantuml-docker-renderer"]
	path = tools/plantuml-docker-renderer
	url = https://github.com/VLMHyperBenchTeam/plantuml-docker-renderer.git

[submodule "tools/release_tool"]
	path = tools/release_tool
	url = https://github.com/VLMHyperBenchTeam/release_tool.git
```

Зафиксируйте изменения в `.gitmodules`:
```bash
git add .gitmodules
git commit -m "Update submodule paths"
```

### Шаг 2: Очистка кэша Git

Проверьте, какие пути подмодулей отслеживаются в индексе:
```bash
git ls-files --stage | grep submodule_name
```

Удалите старые записи из индекса:
```bash
git rm --cached old_path/submodule_name
```

Для нашего случая:
```bash
git rm --cached plantuml-docker-renderer
git rm --cached release_tool
```

### Шаг 3: Синхронизация подмодулей

Выполните синхронизацию и обновление подмодулей:
```bash
git submodule sync --recursive
git submodule update --init --recursive
```

### Шаг 4: Удаление физических копий

Если старые копии подмодулей остались в корне проекта, удалите их:
```bash
rm -rf plantuml-docker-renderer release_tool
```

### Шаг 5: Проверка состояния

Проверьте, что подмодули правильно настроены:
```bash
git submodule status
```

Ожидаемый результат:
```
... tools/plantuml-docker-renderer (...)
... tools/release_tool (...)
```

## Профилактика

Чтобы избежать подобных проблем в будущем:

1. Всегда используйте `git mv` для перемещения подмодулей, если возможно
2. После изменения `.gitmodules`, немедленно выполняйте `git submodule sync`
3. Регулярно проверяйте состояние подмодулей с помощью `git submodule status`
4. При сомнениях, используйте `git ls-files --stage` для проверки актуальных путей в индексе

## Альтернативное решение

Если описанный выше подход не работает, можно использовать полное удаление и повторное добавление подмодуля:

```bash
# 1. Удаление подмодуля
git submodule deinit -f path/to/submodule
git rm --cached path/to/submodule
rm -rf .git/modules/path/to/submodule
# Удалите запись из .gitmodules вручную или с помощью:
# git config --remove-section submodule.path/to/submodule

# 2. Добавление подмодуля с новым путем
git submodule add https://github.com/user/repo.git new/path/to/submodule