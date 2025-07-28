import subprocess
import json
from typing import Dict, List
from pydantic import BaseModel
from vllm import AsyncEngineArgs, AsyncLLMEngine
from vllm.sampling_params import SamplingParams, GuidedDecodingParams
import asyncio
from metrics_invoice import metrics


# Определяем Pydantic модели для структуры данных
class Item(BaseModel):
    name: str
    quantity: str
    unit: str
    price: str
    amount: str


class InvoiceData(BaseModel):
    supplier_name: str
    supplier_address: str
    supplier_actual_address: str
    supplier_inn: str
    supplier_kpp: str
    supplier_ogrn: str
    bank_name: str
    bank_bik: str
    account_number: str
    correspondent_account: str
    invoice_number: str
    invoice_date: str
    payment_terms: str
    payment_conditions: str
    service_period: str
    total_amount: str
    currency: str
    vat_rate: str
    vat_amount: str
    amount_without_vat: str
    items: List[Item]
    basis: str
    contact_person: str
    contact_phone: str
    signature: str


async def get_model_response_with_structured_output(image_path: str, prompt: str) -> Dict:
    """
    Получает ответ от модели с использованием vLLM и guided decoding для гарантированного получения валидного JSON.
    """
    # Загружаем конфигурацию модели
    with open("model_config.json", "r", encoding="utf-8") as f:
        model_config = json.load(f)

    # Извлекаем параметры из конфигурации
    model_name = "Qwen/Qwen2.5-VL-7B-Instruct"
    max_pixels = model_config["specific_params"]["max_pixels"]
    max_model_len = model_config["specific_params"]["max_new_tokens"]
    cache_dir = model_config["common_params"]["cache_dir"]

    # Создаем директорию кэша, если она не существует
    import os

    os.makedirs(cache_dir, exist_ok=True)

    # Настройка асинхронного движка vLLM
    engine_args = AsyncEngineArgs(
        model=model_name,
        dtype="bfloat16",
        tensor_parallel_size=1,
        max_model_len=max_model_len,
        enable_prefix_caching=True,
        mm_processor_kwargs={"max_pixels": max_pixels},
        limit_mm_per_prompt={"image": 1},
        download_dir=os.path.abspath(cache_dir),
    )

    engine = AsyncLLMEngine.from_engine_args(engine_args)

    # Параметры семплирования с guided decoding
    guided_decoding_params = GuidedDecodingParams(
        json=InvoiceData.model_json_schema()
    )

    sampling_params = SamplingParams(
        temperature=0.1, max_tokens=8000, stop=["\n"], guided_decoding=guided_decoding_params
    )

    # Формируем сообщение в формате chat
    messages = [
        {
            "role": "user",
            "content": [{"type": "image", "image": image_path}, {"type": "text", "text": prompt}],
        }
    ]

    # Преобразуем сообщения в строку для vLLM
    prompt_text = ""
    for message in messages:
        if message["role"] == "user":
            for content in message["content"]:
                if content["type"] == "text":
                    prompt_text += content["text"]
                elif content["type"] == "image":
                    prompt_text += "<image>"

    # Генерируем ответ
    results_generator = engine.generate(prompt_text, sampling_params, request_id="0")
    final_output = None

    async for request_output in results_generator:
        final_output = request_output

    if final_output and final_output.outputs:
        try:
            # Возвращаем сгенерированный текст как словарь
            result = json.loads(final_output.outputs[0].text)
            return result
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            print(f"Текст ответа модели: {final_output.outputs[0].text}")
            return {}

    return {}


def evaluate_document_extraction(
    reference: Dict,
    hypothesis: Dict,
    document_fields: List[str],
    item_fields: List[str],
    cer_threshold: float = 0.15,
    item_f1_threshold: float = 0.85,
) -> Dict:
    """
    Оценивает качество извлечения данных из документа.
    Возвращает словарь с метриками.

    Args:
        reference: Словарь с эталонными значениями
        hypothesis: Словарь с предсказанными значениями
        document_fields: Список названий основных полей документа для оценки
        item_fields: Список названий полей позиций для оценки
        cer_threshold: Порог CER для определения правильности поля (по умолчанию 0.15)
        item_f1_threshold: Порог F1-меры для определения правильности позиции (по умолчанию 0.85)

    Returns:
        Словарь с результатами оценки
    """
    return metrics.evaluate_document_extraction(
        reference,
        hypothesis,
        document_fields,
        item_fields,
        cer_threshold,
        item_f1_threshold
    )


async def main():
    """Основная функция для выполнения обработки изображения."""
    # Загрузка промпта
    with open("prompts/erpai/invoice_extraction_prompt.txt", "r", encoding="utf-8") as f:
        prompt = f.read()

    # Пути к данным
    image_path = (
        "datasets/dataset-erpai/invoices/images/2507-483129-77644-Счет на оплату_page_0.png"
    )
    reference_path = (
        "datasets/dataset-erpai/invoices/json/2507-483129-77644-Счет на оплату_page_0.json"
    )

    # Загружаем эталонные данные
    with open(reference_path, "r", encoding="utf-8") as f:
        reference_data = json.load(f)

    # Получаем ответ модели с использованием vLLM и guided decoding
    print("Получаем ответ от модели с использованием vLLM и guided decoding...")
    hypothesis_data = await get_model_response_with_structured_output(image_path, prompt)
    print("Ответ модели:")
    print(json.dumps(hypothesis_data, ensure_ascii=False, indent=2))

    # Определяем структуру полей для оценки
    document_fields = [
        "supplier_name",
        "supplier_address",
        "supplier_actual_address",
        "supplier_inn",
        "supplier_kpp",
        "supplier_ogrn",
        "bank_name",
        "bank_bik",
        "account_number",
        "correspondent_account",
        "invoice_number",
        "invoice_date",
        "payment_terms",
        "payment_conditions",
        "service_period",
        "total_amount",
        "currency",
        "vat_rate",
        "vat_amount",
        "amount_without_vat",
        "basis",
        "contact_person",
        "contact_phone",
        "signature",
    ]

    item_fields = ["name", "quantity", "unit", "price", "amount"]

    # Оцениваем качество извлечения
    evaluation_results = evaluate_document_extraction(
        reference_data, hypothesis_data, document_fields, item_fields
    )

    # Выводим результаты оценки
    print("\n" + "=" * 50)
    print("РЕЗУЛЬТАТЫ ОЦЕНКИ КАЧЕСТВА ИЗВЛЕЧЕНИЯ")
    print("=" * 50)

    print("\nОсновные метрики:")
    print(f"Точность полей: {evaluation_results['overall_metrics']['field_precision']:.3f}")
    print(f"Полнота полей: {evaluation_results['overall_metrics']['field_recall']:.3f}")
    print(f"F1-мера полей: {evaluation_results['overall_metrics']['field_f1']:.3f}")
    print(f"Точность количества позиций: {evaluation_results['item_metrics']['item_accuracy']:.3f}")
    print(f"Средняя F1-мера позиций: {evaluation_results['item_metrics']['average_item_f1']:.3f}")
    print(f"Общая точность: {evaluation_results['overall_metrics']['overall_accuracy']:.3f}")

    # Выводим детали по полям с высоким CER
    print("\nПоля с CER > 15%:")
    high_cer_fields = [
        field
        for field, metrics in evaluation_results["field_metrics"].items()
        if metrics["cer"] > 0.15 and not metrics["correct"]
    ]

    if high_cer_fields:
        for field in high_cer_fields:
            metrics = evaluation_results["field_metrics"][field]
            print(f"  {field}: CER={metrics['cer']:.3f}")
            print(f"    Эталон: {metrics['reference']}")
            print(f"    Модель:  {metrics['hypothesis']}")
    else:
        print("  Все поля извлечены с CER ≤ 15%")

    # Выводим информацию о позициях
    print("\nИнформация о позициях:")
    print(f"  Эталонное количество: {evaluation_results['item_metrics']['reference_count']}")
    print(f"  Извлеченное количество: {evaluation_results['item_metrics']['hypothesis_count']}")
    print(f"  Правильно распознано: {evaluation_results['item_metrics']['correct_count']}")

    # Отображаем использование GPU
    subprocess.run(["nvidia-smi"])


if __name__ == "__main__":
    # Запускаем асинхронную основную функцию
    asyncio.run(main())
