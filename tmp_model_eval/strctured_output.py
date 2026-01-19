import json
import re
import subprocess

from model_interface.model_factory import ModelFactory


def extract_json_from_response(response: str) -> dict:
    """Извлекает JSON из текстового ответа модели."""
    try:
        # Ищем JSON-подобную структуру в ответе
        json_match = re.search(r"\{.*?\}", response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)
        return {"error": "JSON not found in response"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"}


def postprocess_passport_data(data: dict) -> dict:
    """Постобработка извлеченных данных."""
    processed = {}

    # Обработка номера документа
    if "number" in data:
        processed["number"] = re.sub(
            r"\D", "", data["number"]
        )  # Оставляем только цифры

    # Обработка имени
    if "name" in data:
        name = data["name"].strip().upper()
        # Удаляем возможные инициалы
        if " " in name:
            name = name.split(" ")[0]
        processed["name"] = name

    return processed


if __name__ == "__main__":
    # Конфигурация модели
    model_family = "Qwen2.5-VL"
    model_name = "Qwen2.5-VL-3B-Instruct"
    cache_dir = "model_cache"

    # Регистрация модели
    model_class_path = "model_qwen2_5_vl.models:Qwen2_5_VLModel"
    ModelFactory.register_model(model_family, model_class_path)

    model_cfg = {
        "model_name": model_name,
        "system_prompt": "",
        "cache_dir": cache_dir,
        "device_map": "cuda:0",
    }

    # Инициализация модели
    model = ModelFactory.get_model(
        model_family,
    )

    # Путь к изображению паспорта
    image_path = "dataset/passport/images/clean/0.jpg"

    # Промпт с явным указанием формата вывода
    prompt = """
    <image>
    Извлеки данные из российского паспорта. Ответ строго в формате JSON, используя только ключи:
    {"number": "серия и номер документа", "name": "фамилия владельца"}

    Инструкции:
    1. Номер документа: серия (4 цифры) и номер (6 цифр) без пробелов
    2. Фамилия: только кириллицей в верхнем регистре
    3. Не добавляй дополнительный текст или комментарии
    4. Если информация не найдена, используй значение "N/A"

    Пример корректного ответа: {"number": "4512345678", "name": "ИВАНОВ"}
    """

    # Выполнение запроса к модели
    response = model.predict_on_image(image=image_path, prompt=prompt)

    # Извлечение и обработка данных
    raw_data = extract_json_from_response(response)
    processed_data = postprocess_passport_data(raw_data)

    # Вывод результата
    print("\n" + "=" * 50)
    print("Raw model response:")
    print(response)

    print("\n" + "=" * 50)
    print("Processed passport data:")
    print(json.dumps(processed_data, ensure_ascii=False, indent=2))

    # Сохранение результата
    output_path = "passport_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"Results saved to {output_path}")
    subprocess.run(["nvidia-smi"])
