# Анализ возможности создания API-обертки для метрик

## 1. Концепция
Идея заключается в создании собственного легковесного **Proxy/Wrapper API** (на базе FastAPI), который оборачивает вызовы к инференс-движкам (vLLM, SGLang, HF) и обогащает ответ точными метриками производительности.

## 2. Реализуемость (Feasibility)

### 2.1. Техническая сложность: Низкая/Средняя
Написать такой прокси на Python (FastAPI) несложно.

**Алгоритм работы Wrapper:**
1.  Принимает запрос `/v1/chat/completions`.
2.  Засекает `start_time` и текущую память `mem_start` (через `pynvml`).
3.  Проксирует запрос в реальный движок (vLLM/SGLang) локально или по сети.
4.  Получает ответ (stream или batch).
5.  Засекает `end_time` и `mem_end`.
6.  Считает метрики (Latency, Peak Memory Delta).
7.  Возвращает клиенту расширенный ответ, добавляя метрики в поле `usage` или кастомный хедер `X-Performance-Metrics`.

### 2.2. Преимущества
*   **Единый интерфейс**: Оркестратор всегда общается с Wrapper'ом и получает метрики в стандартизированном формате, независимо от бэкенда.
*   **Точность**: Измерения происходят максимально близко к процессу (на том же узле/контейнере).
*   **Гибкость**: Можно добавить любую логику (валидация, логирование, rate limiting) без изменения кода оркестратора.

### 2.3. Ограничения
*   **Overhead**: Небольшая задержка на сериализацию/десериализацию в Python (микросекунды, для VLM не критично).
*   **Streaming**: Для streaming-ответов нужно аккуратно проксировать генератор и замерять TTFT "на лету".

## 3. Архитектура Wrapper'а

```python
# Псевдокод Wrapper
from fastapi import FastAPI, Request
import time
import pynvml
import httpx

app = FastAPI()

@app.post("/v1/chat/completions")
async def proxy_generate(request: Request):
    # 1. Start Metrics
    start_time = time.perf_counter()
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    mem_start = pynvml.nvmlDeviceGetMemoryInfo(handle).used

    # 2. Forward Request to vLLM (localhost:8000)
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/v1/chat/completions", json=await request.json())
    
    # 3. End Metrics
    end_time = time.perf_counter()
    mem_end = pynvml.nvmlDeviceGetMemoryInfo(handle).used
    
    # 4. Enrich Response
    result = response.json()
    result["performance"] = {
        "latency_ms": (end_time - start_time) * 1000,
        "memory_delta_mb": (mem_end - mem_start) / 1024**2,
        "peak_memory_mb": mem_end / 1024**2
    }
    
    return result
```

## 4. Рекомендация
**Да, это отличная идея.** 
Реализация собственного `InferenceServerWrapper` решит проблему отсутствия детальных метрик в стандартных API и унифицирует взаимодействие с разными бэкендами. Это стоит включить в финальную архитектуру как стандартный компонент `InferenceEnv`.