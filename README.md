# Docker контейнер модели

Поддерживаются модели:

P.S. Укажите одно из следующих названий при инициализации класса Qwen2VLModel(model_name="Qwen2.5-VL-3B-Instruct")

Варианты:
* Qwen2.5-VL-3B-Instruct
* Qwen2.5-VL-7B-Instruct

## Скачать к себе Docker-образ

Docker-образ опубликован на `GitHub Packages Container Registry`([ссылка](https://github.com/VLMHyperBenchTeam/model_qwen2.5-vl/pkgs/container/qwen2.5-vl/438485241?tag=ubuntu22.04-cu124-torch2.4.0_eval_v0.1.0)).

```
docker pull ghcr.io/vlmhyperbenchteam/qwen2.5-vl:ubuntu22.04-cu124-torch2.4.0_eval_v0.1.0
```

## Run Docker Container

Для запуска `Docker Container` выполним команду:
```
docker run \
    --gpus all \
    -it \
    -v .:/workspace \
    ghcr.io/vlmhyperbenchteam/qwen2.5-vl:ubuntu22.04-cu124-torch2.4.0_eval_v0.1.0 sh
```

Нам откроется терминал внутри `Docker Container`.

Для запуска предсказаний выполним в нем команду:
```
cd cd workspace
python run_vqa.py
```




# Скачивание данных и промптов
## промптов (старые из Google)

```
docker run \
    --gpus all \
    -it \
    -v .:/workspace \
    ghcr.io/vlmhyperbenchteam/qwen2.5-vl:ubuntu22.04-cu124-torch2.4.0_eval_v0.1.0 python downloaders/download_prompts.py
```

## датасета для обучения (старый из Google)

Скачать старый датасет от Насти.

```
docker run \
    --gpus all \
    -it \
    -v .:/workspace \
    ghcr.io/vlmhyperbenchteam/qwen2.5-vl:ubuntu22.04-cu124-torch2.4.0_eval_v0.1.0 python downloaders/download_dataset.py
```

## Разархивируем датасет для обучения (актуальный из mail.ru)

Если скачивали архив из mail.ru облака отдельными zip-архивами, например, в папку `dataset`.
Переходим в нее и выполняем команду для разархивирования частей датасета:
```bash
for file in *.zip; do unzip "$file"; done
```


# Изменения

## Использование картинок без base64:

* Производительность: убрал кодирование изображений в base64, что снижает использование памяти и ускоряет обработку.
* Упрощение: меньше строк кода, меньше зависимостей.
* Экономия памяти: base64-кодирование увеличивает размер данных примерно на 33%.

# Скрипт limited_tree.py

Скрипт полезен для быстрого просмотра структуры больших проектов без загромождения вывода.

Смотри подробную документацию по его использованию ([ссылка](./docs/limited_tree.md)).

Пример вывода:
```
my_project/
├── src/
│   ├── main.py
│   ├── utils.py
│   └── ... (3 more)
├── tests/
│   ├── test_main.py
│   └── test_utils.py
├── README.md
├── requirements.txt
└── setup.py
```

# Subsets
```
"subsets": ["blur", "noise", "clean", "bright", "gray", "rotated", "spatter"],
```