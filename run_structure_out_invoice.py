import subprocess

import model_qwen2_5_vl.models
from model_interface.model_factory import ModelFactory
from model_interface.model_utils import load_model_config
from prompt_handler import load_prompt

# Константы для путей к файлам
MODEL_CONFIG_PATH = "model_config.json"
PROMPT_PATH = "prompts/erpai/invoice_extraction_prompt.txt"
IMAGE_PATH = (
    "datasets/dataset-erpai/invoices/images/"
    "2507-483129-77644-Счет на оплату_page_0.png"
)


def main():
    """Основная функция для выполнения обработки изображения."""
    # Регистрация моделей
    model_qwen2_5_vl.models.register_models()

    # Загрузка конфигурации модели
    model_config = load_model_config(MODEL_CONFIG_PATH)

    # Инициализация модели
    model = ModelFactory.initialize_model(model_config)

    # Загрузка промпта
    prompt = load_prompt(PROMPT_PATH)

    # Получение ответа модели
    model_answer = model.predict_on_image(image=IMAGE_PATH, prompt=prompt)
    print(model_answer)

    # Отображаем использование GPU
    subprocess.run(["nvidia-smi"])


if __name__ == "__main__":
    main()
