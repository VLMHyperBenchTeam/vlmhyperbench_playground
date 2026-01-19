import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from bench_utils.metrics import calculate_ordering_metrics
from bench_utils.model_utils import initialize_model, load_prompt, prepare_prompt
from bench_utils.utils import (
    get_document_type_from_config,
    get_run_id,
    load_config,
)
from tqdm import tqdm


def get_image_paths_for_document(
    dataset_path: Path, document_id: str, subset_name: str
) -> List[Path]:
    """Получает пути к изображениям страниц для конкретного документа.

    Args:
        dataset_path (Path): Корневой путь к датасету.
        document_id (str): Идентификатор документа.
        subset_name (str): Имя подмножества (например, 'clean', 'blur').

    Returns:
        List[Path]: Список путей к изображениям страниц документа в порядке номеров.
    """
    document_dir = dataset_path / "images" / subset_name / document_id
    if not document_dir.exists():
        return []

    image_files = []
    for i in range(10):
        image_path = document_dir / f"{i}.jpg"
        if image_path.exists():
            image_files.append(image_path)
        else:
            break

    return image_files


def get_document_ids(
    dataset_path: Path, subset_name: str, sample_size: Optional[int] = None
) -> List[str]:
    """Получает список ID документов в указанном подмножестве.

    Args:
        dataset_path (Path): Корневой путь к датасету.
        subset_name (str): Имя подмножества.
        sample_size (Optional[int]): Количество документов для выборки.
                                   Если None, обрабатываются все документы.

    Returns:
        List[str]: Список ID документов.
    """
    subset_dir = dataset_path / "images" / subset_name
    if not subset_dir.exists():
        return []

    document_ids = [d.name for d in subset_dir.iterdir() if d.is_dir()]

    if sample_size is not None:
        document_ids = document_ids[:sample_size]

    return document_ids


def load_ground_truth_dynamic(
    dataset_path: Path, document_id: str, document_type_key: str
) -> List[int]:
    """Загружает правильный порядок страниц из JSON файла для любого типа документа.

    Args:
        dataset_path (Path): Корневой путь к датасету.
        document_id (str): Идентификатор документа.
        document_type_key (str): Ключ типа документа в JSON файле.

    Returns:
        List[int]: Правильный порядок страниц (индексы от 1).
    """
    json_file = dataset_path / "jsons" / f"{document_id}.json"
    if not json_file.exists():
        return []

    with json_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    fields = data.get("fields", {})
    if document_type_key not in fields:
        print(f"Ключ '{document_type_key}' не найден в файле {json_file}")
        print(f"Доступные ключи: {list(fields.keys())}")
        return []

    true_order = fields[document_type_key]
    return [i + 1 for i in true_order]


def extract_json_from_model_output(model_output: str) -> Optional[Dict[str, Any]]:
    if not isinstance(model_output, str):
        print(f"Ожидается строка, получен: {type(model_output)}")
        return None

    cleaned_output = model_output.strip()

    json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned_output, re.DOTALL)
    if json_match:
        json_content = json_match.group(1).strip()
    else:
        json_match = re.search(r"\{.*\}", cleaned_output, re.DOTALL)
        if json_match:
            json_content = json_match.group(0).strip()
        else:
            json_content = cleaned_output

    try:
        return json.loads(json_content)
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        print(f"Содержимое для парсинга: {repr(json_content[:200])}...")
        return None


def extract_ordered_pages_from_json(parsed_json: Dict[str, Any]) -> List[int]:
    if not isinstance(parsed_json, dict):
        print(f"Ожидается словарь, получен: {type(parsed_json)}")
        return []

    if "ordered_pages" in parsed_json:
        pages = parsed_json["ordered_pages"]
        if isinstance(pages, list) and all(isinstance(p, int) for p in pages):
            return pages
        else:
            print(
                f"Значение 'ordered_pages' должно быть списком целых чисел, получено: {pages}"
            )
    else:
        print(
            f"Ключ 'ordered_pages' не найден в JSON. Доступные ключи: {list(parsed_json.keys())}"
        )

    return []


def parse_model_output_fallback(model_output: str) -> List[int]:
    array_match = re.search(r"\[[\d\s,]+\]", model_output)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except json.JSONDecodeError:
            pass

    numbers = re.findall(r"\b[1-9]\b", model_output)
    if numbers:
        try:
            return [int(n) for n in numbers[:4]]
        except ValueError:
            pass

    return []


def process_model_response(model_response: str) -> List[int]:
    if not isinstance(model_response, str):
        print(f"Модель вернула неожиданный тип: {type(model_response)}")
        return []

    parsed_json = extract_json_from_model_output(model_response)
    if parsed_json:
        ordered_pages = extract_ordered_pages_from_json(parsed_json)
        if ordered_pages:
            return ordered_pages

    print("Основной парсинг не удался, пробуем резервный способ...")
    fallback_result = parse_model_output_fallback(model_response)
    if fallback_result:
        print(f"Резервный способ дал результат: {fallback_result}")
        return fallback_result

    print("Не удалось извлечь порядок страниц из ответа модели")
    print(f"Сырой ответ: {repr(model_response[:300])}...")
    return []


def get_prediction(model: Any, image_paths: List[Path], prompt: str) -> List[int]:
    try:
        image_paths_str = [str(path) for path in image_paths]
        model_response = model.predict_on_images(
            images=image_paths_str, prompt=prompt
        )
        return process_model_response(model_response)
    except Exception as e:
        print(f"Ошибка при предсказании для документа: {e}")
        return []


def save_prediction(output_dir: Path, document_id: str, prediction: List[int]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{document_id}.json"

    result = {"ordered_pages": prediction}
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def calculate_and_save_metrics(
    all_metrics: Dict[str, List[float]], subset_name: str, run_id: str
) -> Dict[str, float]:
    if not all_metrics or not any(all_metrics.values()):
        print("Нет данных для вычисления метрик.")
        return {}

    mean_metrics = {
        key: round(sum(values) / len(values), 4) if values else 0.0
        for key, values in all_metrics.items()
    }

    print(f"\n📊 Метрики для сабсета {subset_name}:")
    for key, value in mean_metrics.items():
        print(f"  {key}: {value:.4f}")

    results_df = pd.DataFrame([mean_metrics])
    results_df.to_csv(f"{run_id}_{subset_name}_page_sorting_results.csv", index=False)

    return mean_metrics


def run_evaluation(config: Dict[str, Any]) -> None:
    task_config = config["task"]
    model_config = config["model"]

    dataset_path = Path(task_config["dataset_path"])
    prompt_path = Path(task_config["prompt_path"])
    sample_size = task_config.get("sample_size")
    output_base_dir = Path(task_config["output_dir"])

    model = initialize_model(model_config)

    template = load_prompt(prompt_path)
    prompt = prepare_prompt(template)
    run_id = get_run_id(model_config["model_name"])

    document_type_name = get_document_type_from_config(config, dataset_path)
    print(f"Обрабатываем документы типа: {document_type_name}")

    document_type_key = None
    for key, _name in config.get("document_classes", {}).items():
        if key in dataset_path.name:
            document_type_key = key
            break

    if not document_type_key:
        print(f"Не удалось определить ключ документа для пути {dataset_path}")
        return

    all_subset_metrics = []

    for subset in task_config["subsets"]:
        print(f"\n📂 Обработка сабсета: {subset}")

        document_ids = get_document_ids(dataset_path, subset, sample_size)
        if not document_ids:
            print(f"Нет документов в сабсете {subset}")
            continue

        print(f"Найдено документов для обработки: {len(document_ids)}")

        output_dir = output_base_dir / dataset_path.name / subset

        all_metrics = {
            "kendall_tau": [],
            "accuracy": [],
            "spearman_rho": [],
        }

        for doc_id in tqdm(document_ids, desc=f"Обработка {subset}"):
            image_paths = get_image_paths_for_document(dataset_path, doc_id, subset)
            if len(image_paths) != 4:
                print(
                    f"Документ {doc_id}: ожидается 4 страницы, найдено {len(image_paths)}"
                )
                continue

            true_order = load_ground_truth_dynamic(
                dataset_path, doc_id, document_type_key
            )
            if not true_order:
                print(f"Не удалось загрузить правильный порядок для документа {doc_id}")
                continue

            predicted_order = get_prediction(model, image_paths, prompt)
            if not predicted_order:
                print(f"Не удалось получить предсказание для документа {doc_id}")
                continue

            save_prediction(output_dir, doc_id, predicted_order)

            metrics = calculate_ordering_metrics(true_order, predicted_order)
            for key, value in metrics.items():
                all_metrics[key].append(value)

            print(f"Документ {doc_id}: {metrics}")

        subset_metrics = calculate_and_save_metrics(all_metrics, subset, run_id)
        if subset_metrics:
            all_subset_metrics.append(subset_metrics)

    if all_subset_metrics:
        final_df = pd.DataFrame(all_subset_metrics)
        overall_metrics = final_df.mean()

        print(f"\n📊 Средние метрики по всем сабсетам для {document_type_name}:")
        print(f"  Средняя точность (Accuracy): {overall_metrics['accuracy']:.4f}")
        print(f"  Средний Kendall Tau: {overall_metrics['kendall_tau']:.4f}")
        print(f"  Средний Spearman Rho: {overall_metrics['spearman_rho']:.4f}")

        final_df.to_csv(f"{run_id}_final_page_sorting_results.csv", index=False)


def main() -> None:
    """Главная функция для запуска процесса упорядочивания страниц.

    Загружает конфигурацию и запускает основной цикл оценки.
    """
    try:
        config = load_config("config_page_sorting.json")
        run_evaluation(config)
    except (FileNotFoundError, KeyError) as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
