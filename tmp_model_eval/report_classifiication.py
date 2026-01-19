# Новый скрипт для генерации отчёта классификации
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd  # type: ignore
from bench_utils.utils import get_run_id, load_config  # type: ignore

HEADER = "# 📝 Отчёт по задаче классификации"


def _metrics_row_to_md(metrics: Dict[str, float]) -> str:
    """Формирует строку markdown-таблицы из метрик."""
    return (
        f"| {metrics.get('accuracy', 0):.4f} | {metrics.get('f1', 0):.4f} | "
        f"{metrics.get('precision', 0):.4f} | {metrics.get('recall', 0):.4f} |"
    )


def _df_to_md_table(df: pd.DataFrame, include_index: bool = True) -> str:
    """Конвертирует DataFrame в markdown-таблицу формата GitHub.

    Если зависимость ``tabulate`` не установлена, выводит предупреждение и
    возвращает упрощённое представление с использованием ``DataFrame.to_string``.
    """
    try:
        # Округляем числовые значения до 4 знаков для компактности
        df_formatted = df.copy()
        float_cols = df_formatted.select_dtypes(include="number").columns
        df_formatted[float_cols] = df_formatted[float_cols].round(4)

        return df_formatted.to_markdown(index=include_index, tablefmt="github")  # type: ignore[attr-defined]
    except ImportError:
        warnings.warn("Пакет 'tabulate' не установлен. Отображаем таблицу в текстовом виде. "
                      "Установите 'tabulate' для красивых Markdown-таблиц: pip install tabulate", stacklevel=2)
        return "```\n" + df.to_string(index=include_index) + "\n```"


def _append_md_section(lines: List[str], title: str) -> None:
    """Добавляет заголовок второго уровня в markdown."""
    lines.extend(["", f"## {title}", ""])


def build_report(config_path: Path, output_path: Path) -> None:
    """Формирует файл отчёта на основании результатов `check_classifiication.py`.

    Параметры:
        config_path: путь к конфигурационному JSON, использованному при запуске оценки.
        output_path: путь для сохранения итогового markdown-файла.
    """
    config = load_config(str(config_path))

    task_cfg = config["task"]
    model_cfg = config["model"]
    document_classes: Dict[str, str] = config["document_classes"]

    prompt_path = task_cfg.get("prompt_path")

    md_lines: List[str] = [HEADER, ""]

    # --- Параметры задачи ---
    _append_md_section(md_lines, "Параметры задачи")
    md_lines.append(f"* **Датасет:** `{task_cfg['dataset_path']}`")
    md_lines.append(f"* **Промпт:** `{prompt_path}`")
    md_lines.append(
        f"* **Subsets:** {', '.join(task_cfg.get('subsets', []))}")
    if task_cfg.get("sample_size"):
        md_lines.append(f"* **Sample size:** {task_cfg['sample_size']}")

    # --- Параметры модели ---
    _append_md_section(md_lines, "Параметры модели")
    md_lines.append(f"* **Модель:** `{model_cfg['model_name']}`")
    # Выводим остальные поля конфигурации модели (кроме имени)
    for key, value in model_cfg.items():
        if key == "model_name":
            continue
        md_lines.append(f"* **{key}:** {value}")

    # --- Содержимое промпта ---
    if prompt_path and Path(prompt_path).exists():
        _append_md_section(md_lines, "Содержимое промпта")
        prompt_text = Path(prompt_path).read_text(encoding="utf-8")
        md_lines.append("```text")
        md_lines.append(prompt_text)
        md_lines.append("```")

    # --- Список классов ---
    _append_md_section(md_lines, "Список классов документов")
    md_lines.append("| Ключ | Название |")
    md_lines.append("|------|----------|")
    for k, v in document_classes.items():
        md_lines.append(f"| {k} | {v} |")

    # --- Определяем run_id по имеющимся CSV-файлам ---
    model_name_clean = model_cfg["model_name"].replace(" ", "_")
    prompt_name = Path(prompt_path).stem if prompt_path else "prompt"

    pattern = f"{model_name_clean}_{prompt_name}_*_final_classification_results.csv"
    candidate_files = sorted(Path(".").glob(pattern))
    if candidate_files:
        # Берём самый новый (по имени, так как timestamp входит в имя)
        latest_file = candidate_files[-1]
        run_id = latest_file.stem.replace("_final_classification_results", "")
    else:
        # Фоллбэк — без timestamp (совместимость)
        run_id = get_run_id(model_cfg["model_name"])  # type: ignore

    # --- Итоговые метрики ---
    final_metrics_file = Path(f"{run_id}_final_classification_results.csv")
    if final_metrics_file.exists():
        final_df = pd.read_csv(final_metrics_file)
        final_metrics = final_df.iloc[0].to_dict()
        _append_md_section(md_lines, "Итоговые метрики")
        md_lines.append("| Accuracy | F1-score | Precision | Recall |")
        md_lines.append("|----------|---------|-----------|--------|")
        md_lines.append(_metrics_row_to_md(final_metrics))

    # --- Метрики по сабсетам ---
    subset_metrics: List[Tuple[str, Dict[str, float]]] = []
    for subset in task_cfg.get("subsets", []):
        metrics_file = Path(f"{run_id}_{subset}_classification_results.csv")
        if metrics_file.exists():
            df = pd.read_csv(metrics_file)
            if not df.empty:
                subset_metrics.append((subset, df.iloc[0].to_dict()))

    if subset_metrics:
        _append_md_section(md_lines, "Метрики по сабсетам")
        md_lines.append("| Сабсет | Accuracy | F1-score | Precision | Recall |")
        md_lines.append("|--------|----------|---------|-----------|--------|")
        for subset, metrics in subset_metrics:
            row = _metrics_row_to_md(metrics)
            md_lines.append(f"| {subset} {row[1:]}")  # удаляем первый символ '|' у row

    # --- Метрики по документам (overall) ---
    overall_class_report = Path(f"{run_id}_overall_class_report.csv")
    if overall_class_report.exists():
        df_overall = pd.read_csv(overall_class_report, index_col=0)
        # Оставляем только precision/recall/F1 и убираем агрегированную строку 'accuracy'
        df_overall = df_overall.drop(index=[row for row in ["accuracy"] if row in df_overall.index], errors="ignore")
        _append_md_section(md_lines, "Метрики по документам — общий датасет")
        md_lines.append(_df_to_md_table(df_overall))

    # --- Метрики по документам для каждого сабсета ---
    for subset in task_cfg.get("subsets", []):
        class_rep_file = Path(f"{run_id}_{subset}_class_report.csv")
        if not class_rep_file.exists():
            continue
        df_subset = pd.read_csv(class_rep_file, index_col=0)
        df_subset = df_subset.drop(index=[row for row in ["accuracy"] if row in df_subset.index], errors="ignore")
        _append_md_section(md_lines, f"Метрики по документам — {subset}")
        md_lines.append(_df_to_md_table(df_subset))

    # --- Матрицы ошибок ---
    for subset in task_cfg.get("subsets", []):
        cm_file = Path(f"{run_id}_{subset}_confusion_matrix.csv")
        if not cm_file.exists():
            continue
        cm_df = pd.read_csv(cm_file, index_col=0)
        _append_md_section(md_lines, f"Confusion Matrix — {subset}")
        md_lines.append(_df_to_md_table(cm_df))

    # --- Сохранение ---
    output_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"✅ Отчёт сохранён в {output_path}")


# --- Точка входа ---
if __name__ == "__main__":
    CONFIG_PATH = Path("config_classification.json")

    # Считываем конфиг, чтобы получить имена модели и промпта
    cfg = load_config(str(CONFIG_PATH))
    model_name_clean = cfg["model"]["model_name"].replace(" ", "_")
    prompt_name = Path(cfg["task"].get("prompt_path", "prompt")).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    dyn_report_name = f"report_{model_name_clean}_{prompt_name}_{timestamp}.md"

    # Если явно указан путь в конфиге — используем его, иначе динамический
    report_section = cfg.get("report", {}) if isinstance(cfg, dict) else {}
    OUTPUT_PATH = Path(report_section.get("output_path", dyn_report_name))

    build_report(CONFIG_PATH, OUTPUT_PATH)