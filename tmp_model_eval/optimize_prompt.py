import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch  # type: ignore  # нужен для обработки OutOfMemoryError
from bench_utils.metrics import calculate_classification_metrics  # type: ignore

# --- Внутренние пакеты проекта ---
from bench_utils.model_utils import initialize_model, load_prompt, prepare_prompt  # type: ignore
from tqdm import tqdm

# Переиспользуем вспомогательные функции из скрипта классификации
from check_classifiication import (
    get_image_paths as _collect_image_paths,
)
from check_classifiication import (
    get_prediction as _predict_single,
)

# --- Константы ---
PROMPTS_DIR = Path("prompts")
PROMPTS_DIR.mkdir(exist_ok=True)

# Максимум картинок, отправляемых модели одномоментно при генерации нового промпта
MAX_IMAGES_IN_REQUEST = 4
# Минимальная допустимая длина валидного промпта
MIN_PROMPT_LENGTH = 30
# Сколько изображений каждого класса брать для генерации нового промпта
IMAGES_PER_CLASS = 1


# -------------------------------------------------------------
# Утилиты
# -------------------------------------------------------------

def extract_prompt_from_output(model_output: str) -> str:
    """Извлекает текст промпта из ответа модели.

    Модель может оборачивать результат в тройные кавычки или блоки кода.
    Мы пытаемся вытащить внутренний текст без форматирования.
    """
    if not isinstance(model_output, str):
        raise ValueError("Ответ модели не является строкой")

    cleaned = model_output.strip()

    # Пробуем извлечь из блока ```
    code_match = re.search(r"```(?:[a-zA-Z]*)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    # Пробуем снять кавычки и пробелы в начале/конце
    return cleaned.strip().strip("\"")


def sample_images_for_improvement(
    dataset_path: Path,
    document_classes: Dict[str, str],
    subset: str,
    images_per_class: int,
) -> List[Path]:
    """Сэмплирует *images_per_class* изображений для каждого класса."""
    sampled: List[Path] = []
    for class_name in document_classes.keys():
        class_dir = dataset_path / class_name / "images" / subset
        if not class_dir.exists():
            continue

        all_files: List[Path] = [p for p in class_dir.iterdir() if p.is_file()]
        if len(all_files) > images_per_class:
            sampled.extend(random.sample(all_files, images_per_class))
        else:
            sampled.extend(all_files)
    return sampled


def evaluate_prompt(
    model: Any,
    dataset_path: Path,
    document_classes: Dict[str, str],
    subsets: List[str],
    sample_size: Optional[int],
    prompt_template: str,
) -> float:
    """Вычисляет accuracy для переданного промпта."""

    classes_str = ", ".join(f"{idx}: {name}" for idx, name in enumerate(document_classes.values()))
    prompt = prepare_prompt(prompt_template, classes=classes_str)

    y_true: List[str] = []
    y_pred: List[str] = []

    for subset in subsets:
        image_paths = _collect_image_paths(
            dataset_path,
            list(document_classes.keys()),
            subset,
            sample_size,
        )
        for img_path in tqdm(image_paths, desc=f"Eval {subset}"):
            try:
                class_name = img_path.relative_to(dataset_path).parts[0]
            except ValueError:
                class_name = img_path.parts[-5] if len(img_path.parts) >= 5 else "Unknown"

            y_true.append(class_name)
            y_pred.append(_predict_single(model, img_path, prompt, document_classes))

    metrics = calculate_classification_metrics(y_true, y_pred, document_classes)
    return metrics.get("accuracy", 0.0)


def generate_improved_prompt(
    model: Any,
    images: List[Path],
    current_prompt: str,
) -> str:
    """Запрашивает у модели улучшенную версию текущего промпта."""
    instruction = (
        "Вы — ассистент, который помогает улучшить системный промпт для "
        "задачи классификации документов. В ответе верните ТОЛЬКО новый текст "
        "промпта без каких-либо пояснений, кода или кавычек. Текст должен быть "
        f"не короче {MIN_PROMPT_LENGTH} символов. Улучшите следующий промпт, "
        "чтобы модель точнее классифицировала документы по типам:\n\n"
        f"{current_prompt}\n"
    )

    # Ограничиваем batch, чтобы не словить OOM
    images_batch = images[:MAX_IMAGES_IN_REQUEST]
    images_str = [str(p) for p in images_batch]

    try:
        model_output = model.predict_on_images(images=images_str, prompt=instruction)
    except torch.cuda.OutOfMemoryError:
        # Фолбэк: пробуем с одной картинкой, если всё ещё падает — убираем картинки вовсе
        torch.cuda.empty_cache()
        try:
            model_output = model.predict_on_images(images=[images_str[0]], prompt=instruction)
        except Exception:
            # Последний фолбэк — вызываем только текстовый prompt без изображений
            print("⚠️  OOM при генерации промпта, пробуем без изображений…")
            model_output = model.predict_on_images(images=[], prompt=instruction)
    except AttributeError:
        # На случай, если в конкретной реализации название метода иное.
        model_output = model.predict_on_images(images=images_str, prompt=instruction)  # type: ignore

    return extract_prompt_from_output(model_output)


# -------------------------------------------------------------
# Основной процесс
# -------------------------------------------------------------

def main() -> None:
    config_path = Path("config_prompt_optimization.json")
    if not config_path.exists():
        msg = (
            "Файл конфигурации 'config_prompt_optimization.json' не найден. "
            "Создайте его по образцу 'config_classification.json'."
        )
        raise FileNotFoundError(msg)

    with config_path.open("r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    task_cfg = config["task"]
    model_cfg = config["model"]
    optim_cfg = config.get("optimization", {})

    dataset_path = Path(task_cfg["dataset_path"])
    prompt_path = Path(task_cfg["prompt_path"])
    subsets = task_cfg["subsets"]
    sample_size = task_cfg.get("sample_size")

    num_attempts: int = int(optim_cfg.get("num_attempts", 5))
    subset_for_improve: str = optim_cfg.get("subset_for_improvement", subsets[0])
    images_per_class: int = IMAGES_PER_CLASS

    # --- Инициализация модели ---
    model = initialize_model(model_cfg)

    # --- Базовый промпт ---
    current_prompt_template = load_prompt(prompt_path)
    baseline_acc = evaluate_prompt(
        model,
        dataset_path,
        config["document_classes"],
        subsets,
        sample_size,
        current_prompt_template,
    )
    print(f"Базовая accuracy: {baseline_acc:.4f}\n")

    best_prompt: str = current_prompt_template
    best_acc: float = baseline_acc

    # --- Оптимизация ---
    images_for_update = sample_images_for_improvement(
        dataset_path, config["document_classes"], subset_for_improve, images_per_class
    )
    if not images_for_update:
        raise RuntimeError("Не удалось подобрать изображения для улучшения промпта")

    for attempt in range(1, num_attempts + 1):
        print(f"\n➤ Попытка {attempt}/{num_attempts}")
        candidate_prompt = generate_improved_prompt(
            model, images_for_update, best_prompt
        )

        if (
            not candidate_prompt
            or candidate_prompt == best_prompt
            or len(candidate_prompt.strip()) < MIN_PROMPT_LENGTH
        ):
            print(
                "  ⚠️  Модель не вернула валидный промпт (слишком короткий или повтор). Пропускаем."
            )
            continue

        acc = evaluate_prompt(
            model,
            dataset_path,
            config["document_classes"],
            subsets,
            sample_size,
            candidate_prompt,
        )
        print(f"  ➜ Accuracy с новым промптом: {acc:.4f}")

        # Сохраняем версию промпта
        out_path = PROMPTS_DIR / f"improved_prompt_attempt_{attempt}.txt"
        out_path.write_text(candidate_prompt, encoding="utf-8")
        print(f"  📄 Промпт сохранён: {out_path}")

        if acc > best_acc:
            print("  ✅ Новый промпт лучше предыдущего! Обновляем лучший вариант.")
            best_acc = acc
            best_prompt = candidate_prompt
        else:
            print("  🔸 Новый промпт не превзошёл лучший результат.")

    # --- Финальное решение ---
    if best_acc > baseline_acc:
        print(
            f"\n🎉 Найден улучшенный промпт! Accuracy: {best_acc:.4f} (было {baseline_acc:.4f})"
        )
        # Перезаписываем исходный файл
        prompt_path.write_text(best_prompt, encoding="utf-8")
        print(f"Исходный файл промпта обновлён: {prompt_path}")
    else:
        print("\n😐 Не удалось улучшить промпт. Остаёмся на исходной версии.")


if __name__ == "__main__":
    main()