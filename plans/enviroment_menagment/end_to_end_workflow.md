# End-to-End Workflow: VLMHyperBench + HPM

Этот документ описывает полный цикл запуска бенчмарка, демонстрируя взаимодействие между Оркестратором (Infrastructure Layer) и HyperPackageManager (Environment Layer).

## Сценарий
Запуск оценки двух моделей:
1.  **Qwen2-VL** (требует `vllm-adapter-qwen`).
2.  **DeepSeek-OCR** (требует `vllm-adapter-deepseek` с кастомной логикой).

## 1. Этап планирования (Orchestrator)

1.  **User Input:** Пользователь загружает `user_config.csv` через Web UI.
2.  **Parsing:** Оркестратор парсит конфиг и реестры `registries/models/`.
3.  **Task Graph:** Создается граф задач.
    *   `Task_1`: Inference Qwen2-VL (GPU)
    *   `Task_2`: Inference DeepSeek-OCR (GPU)
    *   `Task_3`: Evaluation (CPU)

## 2. Этап выполнения: Inference (Serving)

### 2.1. Запуск Inference Workers (Orchestrator)
Оркестратор поднимает контейнеры-воркеры. Для обеспечения удаленного запуска (без монтирования томов), конфигурация передается через переменные окружения (Self-Contained Configuration).

В этой схеме `hpm` является **Entrypoint** контейнера (см. [ADR-002: Динамические зависимости](../../../docs_site/docs/architecture/adr/002-dynamic-dependencies.md)).

**Worker 1: Qwen2-VL (Prod / Remote)**
```bash
# HPM на хосте генерирует lock-файл для плагина
# Entrypoint 'serve' уже определен в манифесте плагина vlm-adapter-qwen
LOCK_CONTENT=$(hpm lock --plugins vlm-adapter-qwen --mode prod | base64 -w0)

# Контейнер запускается через hpm entrypoint
# hpm выполняет JIT-установку, а затем запускает команду, связанную с entrypoint 'serve'
docker run -d --name qwen-worker \
  --gpus device=0 \
  --entrypoint hpm \
  -e HPM_LOCK_B64="$LOCK_CONTENT" \
  -e RUN_MODE=prod \
  vlmhyperbench/base-gpu:latest \
  run --entrypoint serve
```

**Worker 2: DeepSeek-OCR (Local Dev)**
Для локальной разработки мы *можем* использовать volume mount для hot-reload.

```bash
docker run -d --name deepseek-worker \
  --gpus device=1 \
  --entrypoint hpm \
  -v /home/user/projects/deepseek-adapter:/packages/deepseek-adapter \
  -e HPM_DEV_OVERLAY='{"deepseek-adapter": "/packages/deepseek-adapter"}' \
  -e RUN_MODE=dev \
  vlmhyperbench/base-gpu:latest \
  run --plugins vlm-adapter-deepseek -- python -m api_wrapper.serve --port 8002
```

### 2.2. Инициализация окружения (HPM inside Workers)
В каждом воркере `hpm` (Entrypoint) выполняет JIT-установку:
1.  **Qwen Worker:** Декодирует `HPM_LOCK_B64`, восстанавливает `uv.lock` и выполняет `uv sync`. Пакеты скачиваются из PyPI.
2.  **DeepSeek Worker:** Видит `RUN_MODE=dev` и оверлей. Устанавливает `vlm-adapter-deepseek` из локальной папки в режиме editable.
3.  **Start Serving:** Запускает `api_wrapper.serve`.

### 2.3. Запуск AnswersGetter (Independent Agent)
Оркестратор запускает `AnswersGetter` как отдельную изолированную среду. Это критически важно, так как разные датасеты могут требовать разных драйверов для итерации (например, DICOM vs HuggingFace Datasets).

**Конфигурация AnswersGetter:**
1.  **Dataset Plugin:** `dataset-snils-loader` (кастомный пакет для чтения специфичного формата).
2.  **Logic Plugin:** `batch-iterator-v2` (стратегия батчинга).

```bash
docker run -d --name answers-getter \
  --entrypoint hpm \
  -v /data:/data \
  -v /registries:/registries \
  -e RUN_MODE=prod \
  vlmhyperbench/base-cpu:latest \
  run --plugins dataset-snils-loader,batch-iterator-v2 -- python -m batch_iterator.main --targets http://qwen-worker:8001,http://deepseek-worker:8002
```

## 3. Процесс Инференса (Data Flow)

1.  **AnswersGetter** инициализирует плагин датасета (через HPM) и начинает итерацию.
2.  Для каждого объекта он формирует S3 URL (например, `s3://bucket/image_01.jpg`) и промпт.
3.  **Async Request:** AnswersGetter отправляет асинхронные HTTP-запросы воркерам:
    *   `POST http://qwen-worker:8001/v1/chat/completions`
    *   `POST http://deepseek-worker:8002/v1/chat/completions`
4.  **Inference (Workers):**
    *   Воркер скачивает изображение из S3 по ссылке.
    *   Выполняет инференс (через загруженный адаптер).
    *   Собирает метрики (Latency, VRAM).
    *   Возвращает JSON-ответ с текстом и метриками.
5.  **Aggregation:** AnswersGetter собирает ответы от всех моделей и сохраняет их в `answers.csv` (или базу данных).

## 4. Изоляция и Масштабирование
*   **Изоляция зависимостей:** Qwen и DeepSeek работают в абсолютно разных контейнерах с разными версиями библиотек (обеспечивается HPM).
*   **Изоляция данных:** Воркеры не имеют доступа к диску с датасетом, они работают только с конкретными объектами по ссылке.
*   **Масштабирование:** Можно поднять 10 `qwen-worker` на разных нодах кластера, и один `AnswersGetter` будет балансировать нагрузку между ними.