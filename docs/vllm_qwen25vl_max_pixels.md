# Документация: Использование параметра max_pixels в vLLM для Qwen2.5-VL

## Обзор

Параметр `max_pixels` позволяет контролировать максимальное разрешение изображений перед их обработкой моделью Qwen2.5-VL в vLLM. Это важный параметр для управления потреблением памяти и производительностью при работе с визуально-языковыми моделями.

## Поддержка в vLLM

Параметр `max_pixels` **поддерживается** в vLLM для модели Qwen2.5-VL, но с определенными особенностями реализации.

## Синтаксис использования

### При инициализации модели

```python
from vllm import LLM

# Пример с ограничением в 768x768 пикселей
llm = LLM(
    model="Qwen/Qwen2.5-VL-3B-Instruct",
    mm_processor_kwargs={"max_pixels": 768 * 768}
)
```

### При запуске сервера

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
    --mm_processor_kwargs {"max_pixels": 518400} \
    --port 8000 \
    --host 0.0.0.0
```

## Важные нюансы

1. **Использование mm_processor_kwargs**: Параметр должен передаваться через `mm_processor_kwargs`, а не напрямую в процессор изображений.

2. **Предупреждения о валидации**: В некоторых версиях vLLM могут возникать предупреждения о том, что `max_pixels` не является валидным аргументом. Это происходит потому, что параметр фильтруется функцией `resolve_mm_processor_kwargs` в `vllm/utils.py`, но при этом все равно корректно применяется.

3. **Оптимизация производительности**: Установка более низкого значения `max_pixels` может значительно ускорить обработку изображений и снизить потребление памяти, особенно при работе с высококачественными изображениями.

## Рекомендации по использованию

- Для баланса качества и производительности рекомендуется начинать с значений в диапазоне 300,000-600,000 пикселей (например, 768×768 = 589,824).
- При работе с ограниченными ресурсами GPU можно снижать значение до 256×256 (65,536 пикселей).
- Для задач, требующих высокой детализации, можно увеличивать значение, но с учетом увеличения потребления памяти.

### Пример полной конфигурации

```python
from vllm import LLM, SamplingParams

# Инициализация модели с ограничением размера изображений
llm = LLM(
    model="Qwen/Qwen2.5-VL-7B-Instruct",
    dtype="bfloat16",
    mm_processor_kwargs={"max_pixels": 768 * 768},
    limit_mm_per_prompt={"image": 5}
)
```

### Параметры генерации
```
sampling_params = SamplingParams(temperature=0.7, max_tokens=512)
```

### Генерация с изображением
```
results = llm.generate({
    "prompt": "Опиши изображение",
    "multi_modal_data": {
        "image": "path/to/image.jpg"
    }
}, sampling_params)
```

# Источники

- [vLLM Documentation: Conserving Memory](https://docs.vllm.ai/en/latest/configuration/conserving_memory.html)
- [vLLM GitHub Issue #13143: Qwen2-VL keyword argument `max_pixels`](https://github.com/vllm-project/vllm/issues/13143)
- [vLLM GitHub Issue #9545: Set max_pixels using LLM.generate](https://github.com/vllm-project/vllm/issues/9545)
- [vLLM Discussion: Speeding up vllm inference for Qwen2.5-VL](https://discuss.vllm.ai/t/speeding-up-vllm-inference-for-qwen2-5-vl/615)
- [Qwen2.5-VL GitHub Repository](https://github.com/QwenLM/Qwen2.5-VL)