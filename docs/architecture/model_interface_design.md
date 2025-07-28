# Архитектура интерфейсов моделирования

## Введение

Данный документ описывает архитектурное решение для поддержки различных бэкендов обработки моделей (Hugging Face, vLLM и др.) в рамках единой системы. Основная цель — обеспечить гибкость выбора бэкенда и режима вывода без дублирования кода в прикладных скриптах.

## Проблема

В текущей реализации:
- [`run_structure_out_invoice_with_metrics.py`](run_structure_out_invoice_with_metrics.py) и
- [`run_structure_out_invoice_with_metrics_vllm.py`](run_structure_out_invoice_with_metrics_vllm.py)

существует значительное дублирование кода, несмотря на использование разных бэкендов (стандартный HF vs vLLM). Каждый скрипт содержит:
- Дублирующиеся списки полей для оценки
- Отдельную логику обработки вывода модели
- Специфичные для бэкенда настройки

## Архитектурное решение

### 1. Двойной интерфейс в model_interface

В пакете [`model_interface`](packages/model_interface/src/model_interface/) реализованы два абстрактных интерфейса:

#### TextModelInterface
```python
class TextModelInterface(Protocol):
    @abstractmethod
    def predict_on_image(self, image: Any, prompt: str) -> str:
        """Предсказание в виде строки"""
        pass
```
Реализуется всеми бэкендами, включая:
- [`model_qwen2.5-vl`](packages/model_qwen2.5-vl/model_qwen2_5_vl/models.py:15)
- [`model_qwen2.5-vl-vllm`](packages/model_qwen2_5_vl_vllm/model_qwen2_5_vl_vllm/vllm_model.py)

#### StructuredModelInterface
```python
class StructuredModelInterface(Protocol):
    @abstractmethod
    def predict_structured(
        self,
        image: Any,
        prompt: str,
        schema: Dict
    ) -> Dict:
        """Предсказание с гарантированной структурой данных"""
        pass
```
Реализуется только бэкендами, поддерживающими структурированный вывод (vLLM).

### 2. Фабрика моделей

[`ModelFactory`](packages/model_interface/src/model_interface/model_factory.py:19) предоставляет два метода:
```python
@classmethod
def get_text_model(cls, model_name: str, params: dict) -> TextModelInterface:
    # Возвращает модель с текстовым выводом

@classmethod
def get_structured_model(cls, model_name: str, params: dict) -> StructuredModelInterface:
    # Возвращает модель со структурированным выводом
```

### 3. Структура пакетов

```
packages/
├── model_interface/          # Абстрактные интерфейсы
├── model_qwen2.5-vl/         # Реализация для Hugging Face
└── model_qwen2.5-vl-vllm/    # Реализация для vLLM
```

Каждый специфичный пакет:
- Реализует необходимые интерфейсы
- Содержит только код, специфичный для бэкенда
- Регистрируется через `ModelFactory.register_model()`

### 4. Конфигурация

[`model_config.json`](model_config.json) поддерживает мультибэкендовую конфигурацию:
```json
{
  "backends": {
    "hf": {
      "common_params": {
        "model_family": "Qwen2.5-VL-HF",
        "package": "model_qwen2_5_vl",
        "module": "models",
        "model_class": "Qwen25VLModel"
      }
    },
    "vllm": {
      "common_params": {
        "model_family": "Qwen2.5-VL-vLLM",
        "package": "model_qwen2_5_vl_vllm",
        "module": "vllm_model",
        "model_class": "Qwen25VLVLLMModel"
      },
      "specific_params": {
        "structured_output": true
      }
    }
  }
}
```

### 5. Схема инвойса

[`invoice_schema.py`](packages/metrics_invoice/src/metrics_invoice/invoice_schema.py) определяет единую схему для всех бэкендов:
```python
class InvoiceSchema(BaseModel):
    supplier_name: str
    # ... все поля документа
    items: List[Item]
```

## Пример использования

### Стандартный режим (текстовый вывод)
```python
from model_interface.model_factory import ModelFactory

model = ModelFactory.get_text_model("Qwen2.5-VL-HF", config)
raw_response = model.predict_on_image(image_path, prompt)
structured_data = repair_json(raw_response)
```

### Структурированный режим (vLLM)
```python
from model_interface.model_factory import ModelFactory
from metrics_invoice.invoice_schema import INVOICE_SCHEMA

model = ModelFactory.get_structured_model("Qwen2.5-VL-vLLM", config)
structured_data = model.predict_structured(image_path, prompt, INVOICE_SCHEMA)
```

## Преимущества архитектуры

1. **Устранение дублирования** — общая логика вынесена в `model_interface`
2. **Гибкость выбора бэкенда** — переключение через конфигурацию
3. **Расширяемость** — добавление новых бэкендов требует только:
   - Создания нового пакета
   - Реализации интерфейсов
   - Регистрации в конфигурации
4. **Тестопригодность** — возможность мокать каждый интерфейс отдельно
5. **Совместимость** — существующие скрипты продолжают работать без изменений

## Рекомендации по использованию

1. Для новых задач используйте `StructuredModelInterface`, если бэкенд поддерживает
2. При добавлении нового бэкенда:
   - Создайте отдельный пакет `model_<название>-<бэкенд>`
   - Реализуйте необходимые интерфейсы
   - Добавьте конфигурацию в `model_config.json`
3. Для оценки используйте единую схему из `invoice_schema.py`

## Диаграмма архитектуры

![model_interface](/docs/architecture/diagrams/model_interface.svg)

Диаграмма расположена в [`docs/architecture/diagrams/model_interface.puml`](/docs/architecture/diagrams/model_interface.puml)