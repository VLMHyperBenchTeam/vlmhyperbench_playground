# Проблема с отображением git-статуса в VS Code при использовании submodules

## Описание проблемы

При работе с git-репозиторием, содержащим submodules, в VS Code может возникнуть ситуация, когда:
- Отображаются только изменения в одном из submodules (например, `plantuml-docker-renderer`)
- Не отображается статус основного репозитория
- При выполнении команды `git status` возникает ошибка: `fatal: not a git repository: packages/bench_utils/../../.git/modules/packages/bench_utils`

Эта проблема обычно связана с повреждением кэша git submodules.

## Методы решения (от простых к радикальным)

### 1. Перезагрузка VS Code (самый безопасный)

**Описание**: Иногда проблема решается простой перезагрузкой редактора.

**Шаги**:
1. Закройте VS Code
2. Откройте VS Code снова
3. Проверьте отображение git-статуса

**Преимущества**: Безопасно, не затрагивает данные

**Недостатки**: Не всегда помогает

### 2. Команда "Developer: Reload Window"

**Описание**: Перезагрузка окна VS Code без полного закрытия приложения.

**Шаги**:
1. Откройте палитру команд (Ctrl+Shift+P)
2. Выберите "Developer: Reload Window"
3. Дождитесь перезагрузки

**Преимущества**: Быстро, безопасно

**Недостатки**: Может не помочь при серьезных проблемах с кэшем

### 3. Обновление submodules

**Описание**: Переинициализация submodules для восстановления их состояния.

**Команда**:
```bash
git submodule update --init --recursive
```

**Преимущества**: Восстанавливает корректное состояние submodules
**Недостатки**: Требует подключения к интернету для загрузки submodules

### 4. Очистка кэша submodules

**Описание**: Полная очистка кэша submodules с последующей переинициализацией.

**Команды**:
```bash
# Очистка кэша
git submodule deinit -f .
# Переинициализация
git submodule update --init --recursive
```

**Преимущества**: Решает большинство проблем с кэшем

**Недостатки**: Требует повторной загрузки данных submodules

### 5. Очистка кэша с принудительным обновлением

**Описание**: Более агрессивная очистка с принудительным обновлением.

**Команды**:
```bash
git submodule deinit -f .
git submodule update --init --recursive --force
```

**Преимущества**: Решает упорные проблемы с кэшем

**Недостатки**: Может перезаписать локальные изменения в submodules

### 6. Полная очистка метаданных submodules

**Описание**: Удаление всех метаданных submodules с последующей полной переинициализацией.

**Команды**:
```bash
# Очистка кэша
git submodule deinit -f .
# Удаление папки с метаданными
rm -rf .git/modules
# Полная переинициализация
git submodule update --init --recursive --force
```

**Преимущества**: Решает практически все проблемы с submodules

**Недостатки**: Требует повторной загрузки всех данных submodules

### 7. Полная переустановка submodules (радикальный метод)

**Описание**: Полное удаление и повторное добавление всех submodules.

**Команды**:
```bash
# Очистка
git submodule deinit -f .
rm -rf .git/modules
# Удаление директорий submodules (сохранив нужные изменения)
rm -rf release_tool
rm -rf packages/model_interface
rm -rf packages/model_qwen2.5-vl
rm -rf packages/bench_utils
rm -rf packages/print_utils
rm -rf packages/hello_world
rm -rf packages/prompt_handler

# Повторное добавление
git submodule add https://github.com/VLMHyperBenchTeam/release_tool.git release_tool
git submodule add https://github.com/VLMHyperBenchTeam/model_interface.git packages/model_interface
git submodule add https://github.com/VLMHyperBenchTeam/model_qwen2.5-vl.git packages/model_qwen2.5-vl
git submodule add https://github.com/VLMHyperBenchTeam/bench_utils.git packages/bench_utils
git submodule add https://github.com/VLMHyperBenchTeam/print_utils.git packages/print_utils
git submodule add https://github.com/VLMHyperBenchTeam/hello_world.git packages/hello_world
git submodule add https://github.com/VLMHyperBenchTeam/prompt_handler.git packages/prompt_handler

# Фиксация изменений
git commit -m "Reinstall submodules"
```

**Преимущества**: Гарантированно решает все проблемы

**Недостатки**: Самый рискованный метод, может привести к потере локальных изменений в submodules

## Рекомендации

1. Начинайте с самых простых методов (1-3)
2. Переходите к более сложным методам только если предыдущие не помогли
3. Перед выполнением радикальных методов (6-7) убедитесь, что все важные изменения сохранены
4. Методы 4-5 решают большинство проблем и являются оптимальным выбором в большинстве случаев

> **Примечание**: Перед выполнением любых команд, связанных с submodules, рекомендуется создать резервную копию важных изменений, особенно если вы работаете с локальными изменениями в submodules.
