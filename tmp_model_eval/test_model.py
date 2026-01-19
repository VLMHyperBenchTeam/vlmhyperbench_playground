"""
Скрипт для тестирования модели Qwen2.5-VL.
Демонстрирует базовую функциональность модели на примере анализа документа.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

# Импорт фабрики моделей
from model_interface.model_factory import ModelFactory

# Функции форматированного вывода перенесены в отдельный пакет print_utils
from print_utils import (  # type: ignore
    print_error,
    print_header,
    print_info,
    print_result,
    print_section,
    print_success,
)


def load_config(config_path: str = "config_test_model.json") -> dict:
    """
    Загружает конфигурацию из JSON файла.

    Args:
        config_path: Путь к файлу конфигурации

    Returns:
        Словарь с конфигурацией
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ ОШИБКА: Файл конфигурации не найден: {config_path}")
        # Fallback конфигурация
        return {
            "task": {
                "image_path": "dataset/passport/images/clean/0.jpg",
                "prompt": "Опиши документ.",
                "show_gpu_info": True
            },
            "model": {
                "model_name": "Qwen2.5-VL-3B-Instruct",
                "device_map": "cuda:0",
                "cache_dir": "./model_cache",
                "system_prompt": ""
            },
            "test_settings": {
                "verbose": True
            }
        }
    except json.JSONDecodeError as e:
        print(f"❌ ОШИБКА при парсинге JSON: {e}")
        return {}


def test_model(
    config_path: str = "config_test_model.json",
    image_path: Optional[str] = None,
    prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    device_map: Optional[str] = None,
    show_gpu_info: Optional[bool] = None
) -> Optional[str]:
    """
    Тестирует модель Qwen2.5-VL на задPанном изображении.

    Args:
        config_path: Путь к файлу конфигурации
        image_path: Путь к изображению для анализа (по умолчанию из конфигурации)
        prompt: Промпт, передаваемый модели (по умолчанию из конфигурации)
        model_name: Имя модели для загрузки (по умолчанию из конфигурации)
        device_map: Устройство для выполнения модели (по умолчанию из конфигурации)
        show_gpu_info: Показывать ли информацию о GPU (по умолчанию из конфигурации)

    Returns:
        Ответ модели или None в случае ошибки
    """
    # Загружаем конфигурацию
    config = load_config(config_path)
    if not config:
        return None

    # Используем значения из конфигурации, если параметры не переданы
    task_config = config.get("task", {})
    model_config = config.get("model", {})
    test_settings = config.get("test_settings", {})

    image_path = image_path or task_config.get("image_path")
    prompt = prompt or task_config.get("prompt") or task_config.get("question")
    model_name = model_name or model_config.get("model_name")
    device_map = device_map or model_config.get("device_map")
    show_gpu_info = show_gpu_info if show_gpu_info is not None else task_config.get("show_gpu_info", False)

    # Настройка путей
    script_dir = Path(__file__).parent
    cache_dir = script_dir / model_config.get("cache_dir", "./model_cache")

    # Проверяем существование изображения
    image_file = Path(image_path)
    if not image_file.exists():
        print_error(f"Изображение не найдено: {image_path}")
        return None

    try:
        # Выводим информацию о задаче
        print_section("ПАРАМЕТРЫ ТЕСТИРОВАНИЯ")
        print_info(f"Модель: {model_name}")
        print_info(f"Устройство: {device_map}")
        print_info(f"Изображение: {image_path}")
        print_info(f"Промпт: {prompt}")

        # Инициализация модели
        print_section("ИНИЦИАЛИЗАЦИЯ МОДЕЛИ")
        print_info("Загрузка модели... (это может занять некоторое время)")

        # Подавляем технические логи если нужно
        show_tech_logs = test_settings.get("show_technical_logs", False)
        if not show_tech_logs:
            # Подавляем предупреждения и технические логи
            import sys
            import warnings
            from io import StringIO
            warnings.filterwarnings("ignore")
            old_stdout = sys.stdout
            sys.stdout = StringIO()

        try:
            model = ModelFactory.initialize_qwen_model(
                model_name=model_name,
                cache_dir=str(cache_dir),
                device_map=device_map,
                system_prompt=model_config.get("system_prompt", "")
            )
        finally:
            # Восстанавливаем вывод
            if not show_tech_logs:
                sys.stdout = old_stdout
                warnings.resetwarnings()

        print_success("Модель успешно загружена!")

        # Тестирование модели
        print_section("ОБРАБОТКА ИЗОБРАЖЕНИЯ")
        print_info("Анализ изображения...")

        # Вызываем метод (реальная реализация использует параметр image, не image_path)
        model_answer = model.predict_on_image(image=image_path, prompt=prompt)

        print_success("Анализ завершен!")

        # Выводим результат
        print_result(model_answer)

        if show_gpu_info:
            show_gpu_status()

        return model_answer

    except Exception as e:
        print_error(f"Ошибка при работе с моделью: {e}")
        return None


def show_gpu_status() -> None:
    """Показывает информацию о состоянии GPU."""
    print_section("ИНФОРМАЦИЯ О GPU")
    try:
        subprocess.run(["nvidia-smi"], check=False)
    except FileNotFoundError:
        print_error("nvidia-smi не найден. Возможно, NVIDIA драйверы не установлены.")


def main():
    """Основная функция для тестирования модели."""
    print_header()

    result = test_model()

    print("\n" + "="*70)
    if result:
        print_success("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
    else:
        print_error("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ОШИБКОЙ!")
    print("="*70)


if __name__ == "__main__":
    main()