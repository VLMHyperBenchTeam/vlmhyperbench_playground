import asyncio
import base64
import json
import os
import uuid
from asyncio import create_task
from pathlib import Path
from typing import Any, Dict

import click
import Levenshtein
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, create_model
from sklearn.metrics import f1_score, precision_score, recall_score
from tqdm.asyncio import tqdm

load_dotenv()

client = AsyncOpenAI(
    base_url=os.getenv("RUNPOD_URL"),
    api_key="token-test",
)


def char_error_rate(gt_str, pred_str):
    return Levenshtein.distance(gt_str, pred_str) / max(1, len(gt_str))


def word_error_rate(gt: str, pred: str) -> float:
    gt_words = gt.strip().split()
    pred_words = pred.strip().split()
    return Levenshtein.distance(" ".join(gt_words), " ".join(pred_words)) / max(
        1, len(gt_words)
    )


def evaluate(gt_path, pred_path, fuzzy_threshold=90):
    rows = []

    gt_path = Path(gt_path)
    pred_path = Path(pred_path)

    files = sorted(gt_path.glob("*.json"))

    for i, gt_file in enumerate(files):
        with open(gt_file, "r", encoding="utf-8") as f:
            gt = json.load(f)
        with open(pred_path / gt_file.name, "r", encoding="utf-8") as f:
            pred = json.load(f)

        for key in gt.keys():
            gt_val = gt.get(key, "").strip()
            pred_val = pred.get(key, "").strip()

            exact_match = int(gt_val == pred_val)

            cer = char_error_rate(gt_val, pred_val)
            wer = word_error_rate(gt_val, pred_val)

            rows.append(
                {
                    "doc_id": i,
                    "field": key,
                    "gt": gt_val,
                    "pred": pred_val,
                    "exact_match": exact_match,
                    "cer": cer,
                    "wer": wer,
                }
            )

    df = pd.DataFrame(rows)

    df["y_true"] = df["gt"] != ""
    df["y_pred"] = df["gt"] == df["pred"]

    precision = precision_score(df["y_true"], df["y_pred"])
    recall = recall_score(df["y_true"], df["y_pred"])
    f1 = f1_score(df["y_true"], df["y_pred"])

    exact_accuracy = df["exact_match"].mean()
    avg_cer = df["cer"].mean()
    avg_wer = df["wer"].mean()

    def compute_field_metrics(group):
        return pd.Series(
            {
                "exact_match": group["exact_match"].mean(),
                "cer": group["cer"].mean(),
                "wer": group["wer"].mean(),
                "precision": precision_score(
                    group["y_true"], group["y_pred"], zero_division=0
                ),
                "recall": recall_score(
                    group["y_true"], group["y_pred"], zero_division=0
                ),
                "f1": f1_score(group["y_true"], group["y_pred"], zero_division=0),
            }
        )

    per_field = df.groupby("field").apply(compute_field_metrics).reset_index()

    return {
        "exact_accuracy": exact_accuracy,
        "avg_cer": avg_cer,
        "avg_wer": avg_wer,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "per_field_metrics": per_field,
        "full_df": df,
    }


def plot_metrics(per_field_df):
    sns.set(style="whitegrid")

    plt.figure(figsize=(10, 5))
    sns.barplot(
        x="cer",
        y="field",
        data=per_field_df.sort_values("cer", ascending=False),
        palette="Reds_r",
    )
    plt.title("CER по полям")
    plt.xlabel("CER")
    plt.ylabel("Поле")
    plt.tight_layout()
    plt.savefig("cer_per_field.png", dpi=300, bbox_inches="tight")

    # Fuzzy Accuracy по полям
    plt.figure(figsize=(10, 5))
    sns.barplot(
        x="fuzzy_match",
        y="field",
        data=per_field_df.sort_values("fuzzy_match", ascending=True),
        palette="Blues",
    )
    plt.title("Fuzzy Accuracy по полям")
    plt.xlabel("Fuzzy Accuracy")
    plt.ylabel("Поле")
    plt.tight_layout()

    plt.savefig(
        "fuzzy_accurcy_per_field.png", dpi=300, bbox_inches="tight"
    )  # ← сохранение графика

    # Exact Match Accuracy по полям
    plt.figure(figsize=(10, 5))
    sns.barplot(
        x="exact_match",
        y="field",
        data=per_field_df.sort_values("exact_match", ascending=True),
        palette="Greens",
    )
    plt.title("Exact Match Accuracy по полям")
    plt.xlabel("Точность (Exact Match)")
    plt.ylabel("Поле")
    plt.tight_layout()
    plt.savefig(
        "exact_match_accurcy_per_field.png", dpi=300, bbox_inches="tight"
    )  # ← сохранение графика

    plt.figure(figsize=(12, 6))


def print_top_errors(per_field_df, top_n=5):
    print("\n📉 Топ", top_n, "полей с самым высоким CER:")
    print(per_field_df.sort_values("cer", ascending=False).head(top_n))

    print("\n❌ Топ", top_n, "полей с самой низкой точностью (Exact Match):")
    print(per_field_df.sort_values("exact_match", ascending=True).head(top_n))


def generate_pydantic_model(
    json_data: Dict[str, Any], model_name: str = "ValidationGenerated"
) -> BaseModel:
    fields = {}

    def get_field_type(value: Any):
        """Определяет тип данных для поля."""
        if isinstance(value, bool):
            return bool
        elif isinstance(value, int):
            return int
        elif isinstance(value, float):
            return float
        elif isinstance(value, str):
            return str
        elif isinstance(value, list):
            # Для списков, создаем тип List[Type]
            return list
        elif isinstance(value, dict):
            # Рекурсивно создаем модель для вложенных словарей
            return generate_pydantic_model(value, "NestedModel")
        else:
            return Any  # Для неопределенных типов

    # Заполняем поля модели
    for key, value in json_data.items():
        fields[key] = (get_field_type(value), ...)

    # Создаем и возвращаем модель
    return create_model(model_name, **fields)


def read_prompt_from_file(filepath):
    with open(filepath, "r") as file:
        content = file.read()
    return content


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        # Encode the image as base64
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode("utf-8")


async def run_request_to_runpod(json_schema, base64_image, prompt, model_name):
    content = [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
        },
    ]
    completion = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": content}],
        extra_body={"guided_json": json_schema},
    )
    return json.loads(completion.choices[0].message.content)


def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


async def process_image(i, dataset_path, prompt, model_name):

    image = dataset_path / "images" / f"{i}.jpg"
    base64_image = image_to_base64(image)
    json_data = read_json_file(str(dataset_path / "jsons" / f"{i}.json"))
    GeneratedModel = generate_pydantic_model(json_data, "StructureModel")
    schema = GeneratedModel.model_json_schema()

    # Вызов асинхронной функции для запроса
    gt = await run_request_to_runpod(schema, base64_image, prompt, model_name)

    # Запись результата в файл
    with open(
        Path("output") / dataset_path.name / "pred" / f"{i}.json", "w", encoding="utf-8"
    ) as f:
        json.dump(gt, f, ensure_ascii=False, indent=4)


async def check_entity_extractor(dataset_path, prompt_path, model_name, subsets):
    run_id = uuid.uuid4()
    subsets = [dataset_path / "images" / subset for subset in subsets]
    print(subsets)
    prompt = read_prompt_from_file(prompt_path)

    all_dfs = []
    all_field_metrics = []

    for subset in subsets:
        subset_name = subset.name
        print(f"\n📂 Обработка сабсета: {subset_name}")

        pred_dir = Path("output") / dataset_path.name / subset_name / "pred"
        pred_dir.mkdir(exist_ok=True, parents=True)

        image_files = sorted(list(subset.glob("*.jpg")))
        semaphore = asyncio.Semaphore(3)

        async def sem_task(i, *, _semaphore=semaphore, _image_files=image_files, _pred_dir=pred_dir):
            async with _semaphore:
                try:
                    image = _image_files[i]
                    image_id = image.stem
                    base64_image = image_to_base64(image)
                    json_data = read_json_file(
                        dataset_path / "jsons" / f"{image_id}.json"
                    )
                    GeneratedModel = generate_pydantic_model(
                        json_data, "StructureModel"
                    )
                    schema = GeneratedModel.model_json_schema()

                    gt = await run_request_to_runpod(
                        schema, base64_image, prompt, model_name
                    )

                    with open(
                        _pred_dir / f"{image_id}.json", "w", encoding="utf-8"
                    ) as f:
                        json.dump(gt, f, ensure_ascii=False, indent=4)
                except Exception as err:
                    print(err)

        tasks = [create_task(sem_task(i)) for i in range(len(image_files))]
        await tqdm.gather(*tasks)

        metrics = evaluate(dataset_path / "jsons", pred_dir)

        print(f"\n📊 Метрики для сабсета {subset_name}:")
        print(f"Exact Match Accuracy: {metrics['exact_accuracy']:.4f}")
        print(f"Average CER: {metrics['avg_cer']:.4f}")
        print(f"Average WER: {metrics['avg_wer']:.4f}")
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall: {metrics['recall']:.4f}")
        print(f"F1-score: {metrics['f1']:.4f}")

        print_top_errors(metrics["per_field_metrics"])

        # Добавляем информацию о сабсете
        metrics["full_df"]["subset"] = subset_name
        metrics["full_df"]["prompt"] = prompt
        metrics["per_field_metrics"]["subset"] = subset_name
        metrics["per_field_metrics"]["prompt"] = prompt

        all_dfs.append(metrics["full_df"])
        all_field_metrics.append(metrics["per_field_metrics"])

        # Сохраняем отдельно
        metrics["full_df"].to_csv(
            f"{run_id}_{subset_name}_detailed_result.csv", index=False
        )
        metrics["per_field_metrics"].to_csv(
            f"{run_id}_{subset_name}_per_field_metrics.csv", index=False
        )

    # Объединение всех результатов
    final_df = pd.concat(all_dfs, ignore_index=True)
    final_field_metrics = pd.concat(all_field_metrics, ignore_index=True)

    # Пересчитываем общие метрики по всем сабсетам
    overall_metrics = {
        "exact_accuracy": (final_df["gt"] == final_df["pred"]).mean(),
        "avg_cer": final_df["cer"].mean(),
        "avg_wer": final_df["wer"].mean(),
        "precision": precision_score(
            final_df["gt"] != "", final_df["gt"] == final_df["pred"]
        ),
        "recall": recall_score(
            final_df["gt"] != "", final_df["gt"] == final_df["pred"]
        ),
        "f1": f1_score(final_df["gt"] != "", final_df["gt"] == final_df["pred"]),
    }

    print("\n📈 Общие метрики по всем сабсетам:")
    for k, v in overall_metrics.items():
        print(f"{k}: {v:.4f}")

    final_df.to_csv(f"{run_id}_ALL_detailed_result.csv", index=False)
    final_field_metrics.to_csv(f"{run_id}_ALL_per_field_metrics.csv", index=False)


@click.command()
@click.option("--dataset-path", type=click.Path(path_type=Path))
@click.option("--prompt-path", type=click.Path(path_type=Path))
@click.option("--model-name", type=str)
@click.option(
    "--subsets",
    type=str,
    default=None,
    help="Список сабсетов через запятую, например: --subsets blur,noise,clean,bright,gray,rotated,spatter",
)
def main(dataset_path, prompt_path, model_name, subsets):
    if not subsets:
        subsets = [d.name for d in (dataset_path / "images").iterdir() if d.is_dir()]
    else:
        subsets = [s.strip() for s in subsets.split(",")]

    asyncio.run(check_entity_extractor(dataset_path, prompt_path, model_name, subsets))


if __name__ == "__main__":
    main()
