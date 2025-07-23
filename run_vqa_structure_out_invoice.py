import subprocess
from typing import Any
from model_qwen2_5_vl import initialize_qwen_model

if __name__ == "__main__":
    # Инициализируем модель одной строкой
    model: Any = initialize_qwen_model(model_name="Qwen2.5-VL-7B-Instruct")

    # Отвечаем на вопрос по одной картинке
    image_path = "datasets/dataset-erpai/invoices/images/2507-483129-77644-Счет на оплату_page_0.png"
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
    model_answer = model.predict_on_image(image=image_path, prompt=question)
    print(model_answer)

    subprocess.run(["nvidia-smi"])

    print(model_answer)