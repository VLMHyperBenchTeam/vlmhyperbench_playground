from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from bench_utils.metrics import calculate_classification_metrics
from bench_utils.model_utils import initialize_model, load_prompt, prepare_prompt
from bench_utils.utils import load_config, save_results_to_csv
from print_utils import (  # type: ignore
    print_error,
    print_header,
    print_info,
    print_section,
    print_success,
)
from sklearn.metrics import classification_report, confusion_matrix  # type: ignore
from tqdm import tqdm


def get_image_paths(
    dataset_path: Path,
    class_names: List[str],
    subset_name: str,
    sample_size: Optional[int] = None,
) -> List[Path]:
    """Собирает пути к изображениям для указанного подмножества данных.

    Функция обходит директории классов и подмножеств, собирая пути к файлам.
    Она корректно обрабатывает случаи, когда изображения находятся как
    непосредственно в папке сабсета, так и в дополнительных подпапках.

    Args:
        dataset_path (Path): Корневой путь к датасету.
        class_names (List[str]): Список имен классов для обработки.
        subset_name (str): Имя подмножества (например, 'clean', 'blur').
        sample_size (Optional[int]): Количество файлов для выборки из каждой
            директории класса. Если None, обрабатываются все файлы.

    Returns:
        List[Path]: Список объектов Path, ведущих к выбранным изображениям.
    """
    selected_files = []
    print_section(f"Обработка сабсета: {subset_name}")
    for class_name in class_names:
        class_dir = dataset_path / class_name / "images" / subset_name
        if not class_dir.exists():
            continue

        paths = list(class_dir.iterdir())
        if sample_size is not None:
            paths = paths[:sample_size]

        for path in paths:
            if path.is_file():
                selected_files.append(path)
            else:
                selected_files.extend(p for p in path.iterdir() if p.is_file())

    print_info(f"Найдено файлов: {len(selected_files)}")
    return selected_files


def get_prediction(
    model: Any, image_path: Path, prompt: str, document_classes: Dict[str, str]
) -> str:
    """Получает предсказание модели для одного изображения.

    Args:
        model (Any): Инициализированный объект модели для классификации.
        image_path (Path): Путь к файлу изображения.
        prompt (str): Промпт, который будет подан модели вместе с изображением.
        document_classes (Dict[str, str]): Словарь классов документов.

    Returns:
        str: Предсказанный ключ класса (например, 'invoice') или 'None'
             в случае ошибки или некорректного ответа модели.
    """
    try:
        # Передаем путь к изображению напрямую в модель
        result = model.predict_on_image(image=str(image_path), prompt=prompt)
        prediction = result.strip().strip('"')

        if prediction.isdigit():
            class_index = int(prediction)
            if 0 <= class_index < len(document_classes):
                pred_class_name = list(document_classes.values())[class_index]
                # Создаем обратное отображение для быстрого поиска ключа класса
                class_names_to_keys = {v: k for k, v in document_classes.items()}
                return class_names_to_keys.get(pred_class_name, "None")
        return "None"

    except Exception as e:
        print_error(f"Ошибка при классификации файла {image_path.name}: {e}")
        return "None"


def calculate_and_save_metrics(
    y_true: List[str],
    y_pred: List[str],
    subset_name: str,
    run_id: str,
    document_classes: Dict[str, str],
) -> Dict[str, float]:
    """Вычисляет и сохраняет метрики, возвращает словарь с основными метриками.

    Args:
        y_true (List[str]): Список истинных меток классов.
        y_pred (List[str]): Список предсказанных меток классов.
        subset_name (str): Имя обрабатываемого подмножества.
        run_id (str): Уникальный идентификатор запуска для именования файлов.
        document_classes (Dict[str, str]): Словарь классов документов.

    Returns:
        Dict[str, float]: Словарь с вычисленными метриками или пустой словарь.
    """
    metrics = calculate_classification_metrics(y_true, y_pred, document_classes)
    if metrics:
        save_results_to_csv(
            metrics, f"{run_id}_{subset_name}_classification_results.csv", subset_name
        )
    return metrics


def calculate_and_save_confusion_matrix(
    y_true: List[str],
    y_pred: List[str],
    subset_name: str,
    run_id: str,
    document_classes: Dict[str, str],
) -> None:
    """Вычисляет матрицу ошибок и сохраняет её в CSV файл.

    Args:
        y_true (List[str]): Список истинных меток классов.
        y_pred (List[str]): Список предсказанных меток классов.
        subset_name (str): Имя сабсета, для которого вычисляется матрица.
        run_id (str): Идентификатор запуска, используется в имени выходного файла.
        document_classes (Dict[str, str]): Словарь классов документов.
    """

    if not y_true:
        print("Нет данных для построения confusion matrix.")
        return

    # Формируем полный список меток, включая возможный класс 'None'
    labels = list(document_classes.keys())
    if "None" in set(y_pred):
        labels.append("None")

    # Обычная (ненормализованная) матрица ошибок — абсолютные количества
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    # Преобразуем в DataFrame и округляем значения для наглядности
    cm_df = pd.DataFrame(cm, index=labels, columns=labels).round(4)

    print_section(f"Confusion Matrix для сабсета {subset_name}")
    print(cm_df)

    cm_filename = f"{run_id}_{subset_name}_confusion_matrix.csv"
    cm_df.to_csv(cm_filename)
    print_success(f"Матрица сохранена в {cm_filename}")


def calculate_and_save_class_report(
    y_true: List[str],
    y_pred: List[str],
    subset_name: str,
    run_id: str,
    document_classes: Dict[str, str],
) -> None:
    """Сохраняет подробный classification_report (precision/recall/F1 per class).

    Args:
        y_true: истинные метки.
        y_pred: предсказанные метки.
        subset_name: имя сабсета или 'overall'.
        run_id: идентификатор запуска.
        document_classes: словарь классов.
    """

    if not y_true:
        return

    all_classes = list(document_classes.keys())
    if "None" in set(y_pred):
        all_classes.append("None")

    report = classification_report(
        y_true, y_pred, labels=all_classes, output_dict=True, zero_division=0
    )

    report_df = pd.DataFrame(report).transpose().round(4)

    out_path = f"{run_id}_{subset_name}_class_report.csv"
    report_df.to_csv(out_path)
    print_success(f"Отчёт по классам сохранён в {out_path}")


def run_evaluation(config: Dict[str, Any]) -> None:
    """Основной цикл оценки модели.

    Оркестрирует весь процесс: от загрузки конфигурации и инициализации
    модели до итерации по подмножествам, сбора предсказаний и расчета
    итоговых средних метрик.

    Args:
        config (Dict[str, Any]): Словарь с полной конфигурацией для запуска,
                                содержащий секции 'task', 'model' и 'document_classes'.
    """
    # --- Вывод параметров перед стартом ---
    print_header()
    print_section("ПАРАМЕТРЫ ОЦЕНКИ")

    task_config = config["task"]
    model_config = config["model"]
    document_classes = config["document_classes"]

    print_info(f"Датасет: {task_config['dataset_path']}")
    print_info(f"Subsets: {', '.join(task_config['subsets'])}")
    if task_config.get("sample_size"):
        print_info(f"Sample size: {task_config['sample_size']}")
    print_info(f"Модель: {model_config['model_name']}")

    dataset_path = Path(task_config["dataset_path"])
    prompt_path = Path(task_config["prompt_path"])
    sample_size = task_config.get("sample_size")

    model = initialize_model(model_config)

    template = load_prompt(prompt_path)
    classes_str = ", ".join(
        f"{idx}: {name}" for idx, name in enumerate(document_classes.values())
    )
    prompt = prepare_prompt(template, classes=classes_str)

    # Формируем уникальный run_id = <model>_<prompt>_<YYYYMMDD_HHMMSS>
    model_name_clean = model_config["model_name"].replace(" ", "_")
    prompt_name = prompt_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{model_name_clean}_{prompt_name}_{timestamp}"
    all_metrics = []

    for subset in task_config["subsets"]:
        image_paths = get_image_paths(
            dataset_path, list(document_classes.keys()), subset, sample_size
        )

        if not image_paths:
            continue

        y_true, y_pred = [], []
        for path in tqdm(image_paths, desc=f"Обработка {subset}"):
            try:
                # Имя класса всегда является первым сегментом после корневой директории датасета.
                class_name = path.relative_to(dataset_path).parts[0]
            except ValueError:
                # На случай, если path не является прямым потомком dataset_path
                class_name = path.parts[-5] if len(path.parts) >= 5 else "Unknown"

            y_true.append(class_name)
            y_pred.append(get_prediction(model, path, prompt, document_classes))

        subset_metrics = calculate_and_save_metrics(
            y_true, y_pred, subset, run_id, document_classes
        )
        # --- Confusion matrix ---
        calculate_and_save_confusion_matrix(
            y_true, y_pred, subset, run_id, document_classes
        )
        # --- Class-wise detailed metrics ---
        calculate_and_save_class_report(
            y_true, y_pred, subset, run_id, document_classes
        )
        if subset_metrics:
            all_metrics.append(subset_metrics)

    # --- Общий отчёт по классам на всём датасете ---
    if y_true and y_pred:
        calculate_and_save_class_report(
            y_true, y_pred, "overall", run_id, document_classes
        )

    if all_metrics:
        final_df = pd.DataFrame(all_metrics)
        avg_metrics = final_df.mean()
        print_section("Средние метрики по всем сабсетам")
        print_info(f"Средняя точность (Accuracy): {avg_metrics['accuracy']:.4f}")
        print_info(f"Средний F1-score: {avg_metrics['f1']:.4f}")
        print_info(f"Средняя точность (Precision): {avg_metrics['precision']:.4f}")
        print_info(f"Средний отзыв (Recall): {avg_metrics['recall']:.4f}")

        out_file = f"{run_id}_final_classification_results.csv"
        final_df.to_csv(out_file, index=False)
        print_success(f"Итоговые метрики сохранены в {out_file}")


def main() -> None:
    """Главная функция для запуска процесса классификации.

    Загружает конфигурацию и запускает основной цикл оценки.
    """
    try:
        config = load_config("config_classification.json")
        run_evaluation(config)
    except (FileNotFoundError, KeyError) as e:
        print_error(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
