import subprocess
import json
from typing import Any, Dict, List


from model_qwen2_5_vl import initialize_qwen_model
from jiwer import cer


def calculate_cer_score(reference: str, hypothesis: str) -> float:
    """
    Рассчитывает CER (Character Error Rate) между эталонным и предсказанным текстом.
    Возвращает значение от 0 до 1, где 0 - полное совпадение.
    """
    if not reference and not hypothesis:
        return 0.0
    if not reference or not hypothesis:
        return 1.0

    return cer(reference, hypothesis)


def is_field_correct(cer_score: float, threshold: float = 0.15) -> bool:
    """
    Определяет, правильно ли извлечено поле на основе порога CER.
    По умолчанию порог 15%.
    """
    return cer_score <= threshold


def calculate_item_f1(
    item_reference: Dict, item_hypothesis: Dict, item_fields: List[str], cer_threshold: float = 0.15
) -> float:
    """
    Рассчитывает F1-меру для одной позиции (item) на основе CER для каждого поля.

    Args:
        item_reference: Словарь с эталонными значениями полей позиции
        item_hypothesis: Словарь с предсказанными значениями полей позиции
        item_fields: Список названий полей, которые нужно оценить
        cer_threshold: Порог CER для определения правильности поля (по умолчанию 0.15)

    Returns:
        F1-мера для позиции
    """
    if not item_reference or not item_hypothesis:
        return 0.0

    correct_fields = 0
    total_fields = len(item_fields)

    for field in item_fields:
        ref_value = str(item_reference.get(field, ""))
        hyp_value = str(item_hypothesis.get(field, ""))
        field_cer = calculate_cer_score(ref_value, hyp_value)
        if is_field_correct(field_cer, cer_threshold):
            correct_fields += 1

    precision = correct_fields / total_fields if total_fields > 0 else 0
    recall = correct_fields / total_fields if total_fields > 0 else 0

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


def is_item_correct(f1_score: float, threshold: float = 0.85) -> bool:
    """
    Определяет, правильно ли распознана позиция на основе порога F1-меры.
    По умолчанию порог 85%.
    """
    return f1_score >= threshold


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
    results = {"field_metrics": {}, "item_metrics": {}, "overall_metrics": {}}

    # Оценка основных полей
    correct_fields = 0
    total_fields = len(document_fields)

    for field in document_fields:
        ref_value = str(reference.get(field, ""))
        hyp_value = str(hypothesis.get(field, ""))
        field_cer = calculate_cer_score(ref_value, hyp_value)
        field_correct = is_field_correct(field_cer)

        results["field_metrics"][field] = {
            "reference": ref_value,
            "hypothesis": hyp_value,
            "cer": field_cer,
            "correct": field_correct,
        }

        if field_correct:
            correct_fields += 1

    # Оценка позиций (items)
    ref_items = reference.get("items", [])
    hyp_items = hypothesis.get("items", [])

    item_f1_scores = []
    correct_items = 0
    total_items = len(ref_items)

    # Сравниваем позиции по порядку
    for i in range(min(len(ref_items), len(hyp_items))):
        item_f1 = calculate_item_f1(ref_items[i], hyp_items[i], item_fields, cer_threshold)
        item_f1_scores.append(item_f1)

        if is_item_correct(item_f1, item_f1_threshold):
            correct_items += 1

    # Если в гипотезе больше позиций, оцениваем оставшиеся как неправильные
    for _ in range(len(hyp_items), len(ref_items)):
        item_f1_scores.append(0.0)

    # Если в эталоне больше позиций, они не будут учтены в correct_items
    avg_item_f1 = sum(item_f1_scores) / len(item_f1_scores) if item_f1_scores else 0.0

    results["item_metrics"] = {
        "reference_count": len(ref_items),
        "hypothesis_count": len(hyp_items),
        "correct_count": correct_items,
        "item_f1_scores": item_f1_scores,
        "average_item_f1": avg_item_f1,
        "item_accuracy": correct_items / total_items if total_items > 0 else 0.0,
    }

    # Общие метрики
    field_precision = correct_fields / total_fields if total_fields > 0 else 0.0
    field_recall = correct_fields / total_fields if total_fields > 0 else 0.0

    if field_precision + field_recall == 0:
        field_f1 = 0.0
    else:
        field_f1 = 2 * (field_precision * field_recall) / (field_precision + field_recall)

    results["overall_metrics"] = {
        "field_accuracy": correct_fields / total_fields,
        "field_precision": field_precision,
        "field_recall": field_recall,
        "field_f1": field_f1,
        "item_count_accuracy": 1.0 if len(ref_items) == len(hyp_items) else 0.0,
        "overall_accuracy": (correct_fields + correct_items) / (total_fields + total_items)
        if (total_fields + total_items) > 0
        else 0.0,
    }

    return results


if __name__ == "__main__":
    # Инициализируем модель
    model: Any = initialize_qwen_model(model_name="Qwen2.5-VL-7B-Instruct")

    # Пути к данным
    image_path = "datasets/dataset-erpai/invoices/images/2507-483129-77644-Счет на оплату_page_0.png"  # noqa: E501
    reference_path = "datasets/dataset-erpai/invoices/json/2507-483129-77644-Счет на оплату_page_0.json"  # noqa: E501

    # Загружаем эталонные данные
    with open(reference_path, "r", encoding="utf-8") as f:
        reference_data = json.load(f)

    # Формируем вопрос для модели
    question = """
Подано изображение счета.
Пожалуйста, извлеките информацию и представьте её в виде структурированного JSON-объекта с указанными полями.

Поля для извлечения:
- "supplier_name": Наименование компании-поставщика
- "supplier_address": Юридический адрес поставщика
- "supplier_actual_address": Фактический адрес (если отличается)
- "supplier_inn": ИНН поставщика
- "supplier_kpp": КПП поставщика
- "supplier_ogrn": ОГРН поставщика
- "bank_name": Название банка
- "bank_bik": БИК банка
- "account_number": Номер счета
- "correspondent_account": Корреспондентский счет
- "invoice_number": Номер счета
- "invoice_date": Дата выставления (в формате DD.MM.YYYY)
- "payment_terms": Срок оплаты
- "payment_conditions": Условия оплаты
- "service_period": Период оказания услуг
- "total_amount": Сумма к оплате
- "currency": Валюта расчетов
- "vat_rate": Ставка НДС
- "vat_amount": Сумма НДС
- "amount_without_vat": Сумма без НДС
- "items": Список товаров/услуг (см. структуру ниже)
- "basis": Основание для выставления счета
- "contact_person": Контактное лицо
- "contact_phone": Контактный телефон
- "signature": Подпись уполномоченного лица

Структура товаров/услуг:
{
  "name": "Наименование товара/услуги",
  "quantity": "Количество",
  "unit": "Единица измерения",
  "price": "Цена за единицу",
  "amount": "Стоимость позиции"
}

JSON-структура:
{
  "supplier_name": "",
  "supplier_address": "",
  "supplier_actual_address": "",
  "supplier_inn": "",
  "supplier_kpp": "",
  "supplier_ogrn": "",
  "bank_name": "",
  "bank_bik": "",
  "account_number": "",
  "correspondent_account": "",
  "invoice_number": "",
  "invoice_date": "",
  "payment_terms": "",
  "payment_conditions": "",
  "service_period": "",
  "total_amount": "",
  "currency": "",
  "vat_rate": "",
  "vat_amount": "",
  "amount_without_vat": "",
  "items": [],
  "basis": "",
  "contact_person": "",
  "contact_phone": "",
  "signature": ""
}
"""

    # Получаем ответ модели
    model_answer = model.predict_on_image(image=image_path, prompt=question)
    print("Ответ модели:")
    print(model_answer)

    # Пытаемся распарсить ответ модели
    try:
        hypothesis_data = json.loads(model_answer)
    except json.JSONDecodeError as e:
        print(f"Ошибка при парсинге JSON: {e}")
        print("Попробуем извлечь JSON из текста...")
        # Простая попытка найти JSON в тексте
        import re

        json_match = re.search(r"\{[\s\S]*\}", model_answer)
        if json_match:
            try:
                hypothesis_data = json.loads(json_match.group())
            except json.JSONDecodeError as e2:
                print(f"Не удалось извлечь валидный JSON: {e2}")
                hypothesis_data = {}
        else:
            print("Не удалось найти JSON в ответе модели")
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
