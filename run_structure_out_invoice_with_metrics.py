import subprocess
import json
from typing import Dict, List

import model_qwen2_5_vl.models
from model_interface.model_factory import ModelFactory
from model_interface.model_utils import load_model_config
from prompt_handler import load_prompt
from json_repair import repair_json
from metrics_invoice import metrics


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


if __name__ == "__main__":
    # Регистрация моделей
    model_qwen2_5_vl.models.register_models()

    # Загрузка конфигурации модели
    model_config = load_model_config("model_config.json")

    # Инициализация модели
    model = ModelFactory.initialize_model(model_config)

    # Загрузка промпта
    prompt = load_prompt("prompts/erpai/invoice_extraction_prompt_improved.txt")

    # Пути к данным
    image_path = "datasets/dataset-erpai/invoices/images/2507-483129-77644-Счет на оплату_page_0.png"
    reference_path = "datasets/dataset-erpai/invoices/json/2507-483129-77644-Счет на оплату_page_0.json"

    # Загружаем эталонные данные
    with open(reference_path, "r", encoding="utf-8") as f:
        reference_data = json.load(f)

    # Получаем ответ модели
    model_answer = model.predict_on_image(image=image_path, prompt=prompt)
    print("Ответ модели:")
    print(model_answer)

    # Пытаемся распарсить ответ модели
    try:
        # Удаляем markdown-разметку, если она присутствует
        cleaned_answer = model_answer.strip()
        if cleaned_answer.startswith("```json"):
            cleaned_answer = cleaned_answer[7:]
        if cleaned_answer.endswith("```"):
            cleaned_answer = cleaned_answer[:-3]
        cleaned_answer = cleaned_answer.strip()

        # Заменяем некорректные символы с помощью регулярного выражения
        import re
        cleaned_answer = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned_answer)

        # Пробуем исправить и распарсить JSON
        hypothesis_data = repair_json(cleaned_answer, return_objects=True)
    except Exception as e:
        print(f"Ошибка при обработке JSON: {e}")
        print("Оригинальный ответ модели:")
        print(model_answer)
        hypothesis_data = {}

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
    evaluation_results = evaluate_document_extraction(reference_data, hypothesis_data, document_fields, item_fields)  # noqa: E501

    # Выводим результаты оценки
    print("\n" + "=" * 50)
    print("РЕЗУЛЬТАТЫ ОЦЕНКИ КАЧЕСТВА ИЗВЛЕЧЕНИЯ")
    print("=" * 50)

    print("\nОсновные метрики:")
    print(f"Точность полей: {evaluation_results['overall_metrics']['field_precision']:.3f}")  # noqa: E501
    print(f"Полнота полей: {evaluation_results['overall_metrics']['field_recall']:.3f}")  # noqa: E501
    print(f"F1-мера полей: {evaluation_results['overall_metrics']['field_f1']:.3f}")  # noqa: E501
    print(f"Точность количества позиций: {evaluation_results['item_metrics']['item_accuracy']:.3f}")  # noqa: E501
    print(f"Средняя F1-мера позиций: {evaluation_results['item_metrics']['average_item_f1']:.3f}")  # noqa: E501
    print(f"Общая точность: {evaluation_results['overall_metrics']['overall_accuracy']:.3f}")  # noqa: E501

    # Выводим детали по полям с высоким CER
    print("\nПоля с CER > 15%:")
    high_cer_fields = [field for field, metrics in evaluation_results["field_metrics"].items() if metrics["cer"] > 0.15 and not metrics["correct"]]  # noqa: E501

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
    print(f"  Эталонное количество: {evaluation_results['item_metrics']['reference_count']}")  # noqa: E501
    print(f"  Извлеченное количество: {evaluation_results['item_metrics']['hypothesis_count']}")  # noqa: E501
    print(f"  Правильно распознано: {evaluation_results['item_metrics']['correct_count']}")  # noqa: E501

    subprocess.run(["nvidia-smi"])
