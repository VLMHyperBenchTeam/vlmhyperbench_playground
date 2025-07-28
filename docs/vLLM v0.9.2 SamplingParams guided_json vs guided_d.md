<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# vLLM v0.9.2 SamplingParams guided_json vs guided_decoding vs extra_body отвечай на русском

В vLLM v0.9.2 параметры SamplingParams позволяют управлять генерацией текстов с помощью нескольких механизмов структурирования вывода. Рассмотрим различия между guided_json, guided_decoding и extra_body:

### 1. **guided_json**

- Предназначен для генерации текста, строго соответствующего заданной схеме JSON.
- Схема обычно задаётся в формате JSON Schema (например, определяя свойства и их типы).
- Пример использования: если вы хотите, чтобы модель гарантированно выдавала валидный JSON-ответ определённой структуры.
- Под капотом реализовано через GuidedDecodingParams с параметром `json`. Передаёте схему – получаете гарантируемую структуру (хотя гарантии завершения структуры всегда нет, если ограничено количество токенов)[^1][^2].


### 2. **guided_decoding**

- Это общий механизм направленной (guided) генерации, который может использовать разные стратегии ограничения пространства токенов.
- Поддерживаемые опции через GuidedDecodingParams:
    - **json**: как выше, для жёсткой структуры.
    - **regex**: регулярные выражения.
    - **choice**: разрешённые варианты ответа (например, ["Yes", "No"]).
    - **grammar**: вывод по контекстно-свободной грамматике.
    - **structural_tag**: структура через XML/разметку.
- Используется в SamplingParams, например:

```python
guided_decoding_params = GuidedDecodingParams(choice=["Positive", "Negative"])
sampling_params = SamplingParams(guided_decoding=guided_decoding_params)
```

- Даёт гибкий способ контролировать формат и разрешённые конструкции вывода[^1][^3].


### 3. **extra_body**

- Используется преимущественно при взаимодействии через OpenAI-совместимый API (например, через клиент openai-python).
- Позволяет прокидывать в запрос дополнительные параметры SamplingParams, которые по умолчанию не поддерживаются стандартным API.
- Например, если нужно установить специфические значения top_k, top_p, temperature для конкретного запроса, их можно передать именно через extra_body.
- Это способ "обойти" ограничения стандартного OpenAI API и использовать все возможности SamplingParams vLLM[^4][^5][^6].


#### Кратко:

- **guided_json** — строгое следование JSON-схеме; это частный случай guided_decoding (стратегия «json»).
- **guided_decoding** — абстракция для различных режимов направленной генерации, включая json, choice, regex и др.
- **extra_body** — "контейнер" для передачи любых дополнительных sampling-параметров через OpenAI-совместимый сервер vLLM, что даёт гибкость при интеграции и использовании полного арсенала SamplingParams.


#### Пример:

```python
# guided_json через SamplingParams
sampling_params = SamplingParams(guided_decoding=GuidedDecodingParams(json=my_json_schema))

# guided_decoding с выбором из вариантов
sampling_params = SamplingParams(guided_decoding=GuidedDecodingParams(choice=["Да", "Нет"]))

# extra_body при работе через openai API
extra_body = {'top_p': 0.8, 'top_k': 40, 'temperature': 0.7}
client.completions.create(prompt="...", extra_body=extra_body)
```


##### Советы:

- Для генерации валидного структурированного вывода используйте guided_json, если задача — жёсткая структура (например, JSON-ответ для API).
- Для более гибких сценариев или внедрения собственных правил генерации — guided_decoding.
- Для настройки sampling при работе через OpenAI-совместимый сервер — extra_body.

[^1][^3][^4][^2][^5][^6]

<div style="text-align: center">⁂</div>

В vLLM v0.9.2 основные различия между guided_json и guided_decoding заключаются в следующем:

- **guided_json** — это частный случай guided_decoding, который используется специально для генерации вывода строго по заданной JSON-схеме. Вы задаёте структуру через JSON Schema, и модель старается сгенерировать ответ, который этой схеме соответствует. В SamplingParams параметр guided_json реализован через GuidedDecodingParams с типом стратегии «json».

- **guided_decoding** — это более общий механизм направленной генерации, который включает разные стратегии контроля вывода: по JSON-схеме («json»), по регулярному выражению («regex»), выбору из заранее определённых вариантов («choice»), грамматике («grammar»), тегам разметки («structural_tag») и другим. То есть guided_decoding — это универсальный контейнер для разных методов структурирования вывода, а guided_json — всего лишь один из них.

Таким образом:
- Если вам нужно сгенерировать строго определённый по структуре JSON, используйте guided_json.
- Если вы хотите ограничивать генерацию не только по JSON, но и по другим правилам (например, выбор из списка, regex и т.д.), используйте guided_decoding и выбирайте нужную стратегию.

[^1]: https://docs.vllm.ai/en/latest/features/structured_outputs.html

[^2]: https://github.com/vllm-project/vllm/issues/8350

[^3]: https://docs.vllm.ai/en/v0.8.2/features/structured_outputs.html

[^4]: https://github.com/vllm-project/vllm/issues/10578

[^5]: https://docs.vllm.ai/en/v0.4.1/serving/openai_compatible_server.html

[^6]: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html

[^7]: https://docs.vllm.ai/en/v0.9.1/api/vllm/sampling_params.html

[^8]: https://github.com/vllm-project/vllm/issues/19954

[^9]: https://docs.vllm.ai/en/v0.8.3/api/inference_params.html

[^10]: https://docs.vllm.ai/en/v0.9.2/api/vllm/entrypoints/llm.html

[^11]: https://github.com/vllm-project/vllm-ascend/issues/1743

[^12]: https://docs.vllm.ai/en/v0.8.4/api/inference_params.html

[^13]: https://docs.vllm.ai/en/v0.9.2/api/vllm/entrypoints/openai/protocol.html

[^14]: https://docs.vllm.ai/en/v0.9.2/api/vllm/engine/llm_engine.html

[^15]: https://docs.vllm.ai/en/v0.9.2/api/vllm/sampling_params.html?q=

[^16]: https://docs.vllm.ai/en/stable/getting_started/quickstart.html

[^17]: https://github.com/vllm-project/vllm-ascend/issues/1798

[^18]: https://github.com/vllm-project/vllm/issues/7337

[^19]: https://docs.vllm.ai/en/v0.8.2/api/inference_params.html

[^20]: https://vllm-ascend.readthedocs.io/en/latest/tutorials/single_npu_multimodal.html

