#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


SUPPORTED_METRICS = ["test_macro_f1", "test_accuracy", "test_balanced_accuracy"]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def format_float(value: float | int | None, digits: int = 4) -> str:
    if value is None:
        return "-"
    return f"{float(value):.{digits}f}"


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    split = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([head, split] + body)


def select_best_run(df: pd.DataFrame, metric: str) -> pd.Series:
    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found in run summary columns: {list(df.columns)}")
    sort_cols = [metric]
    if "test_accuracy" in df.columns and metric != "test_accuracy":
        sort_cols.append("test_accuracy")
    if "val_macro_f1" in df.columns:
        sort_cols.append("val_macro_f1")
    return df.sort_values(by=sort_cols, ascending=False).iloc[0]


def confusion_to_markdown(confusion: list[list[int]], labels: list[str]) -> str:
    headers = ["actual \\ predicted"] + labels
    rows: list[list[str]] = []
    for i, actual in enumerate(labels):
        rows.append([actual] + [str(int(confusion[i][j])) for j in range(len(labels))])
    return table(headers, rows)


def top_confusions(confusion: list[list[int]], labels: list[str], k: int = 3) -> list[tuple[str, str, int]]:
    pairs: list[tuple[str, str, int]] = []
    for i, actual in enumerate(labels):
        for j, predicted in enumerate(labels):
            if i == j:
                continue
            count = int(confusion[i][j])
            if count > 0:
                pairs.append((actual, predicted, count))
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs[:k]


def build_model_comparison(df: pd.DataFrame) -> str:
    rows: list[list[str]] = []
    ordered = df.sort_values(by=["test_macro_f1", "test_accuracy"], ascending=False)
    for _, row in ordered.iterrows():
        rows.append(
            [
                str(row["run_name"]),
                str(row["model"]),
                format_float(row.get("val_macro_f1")),
                format_float(row.get("test_macro_f1")),
                format_float(row.get("test_accuracy")),
                format_float(row.get("test_balanced_accuracy")),
            ]
        )
    return table(
        ["run_name", "model", "val_macro_f1", "test_macro_f1", "test_accuracy", "test_balanced_accuracy"],
        rows,
    )


def build_dataset_section(summary: dict) -> str:
    total_rows = int(summary.get("total_rows", 0))
    split_sizes = summary.get("split_sizes", {})
    label_distribution = summary.get("label_distribution", {})
    source_stats = summary.get("source_stats", {})

    label_rows: list[list[str]] = []
    for label, count in sorted(label_distribution.items(), key=lambda x: x[1], reverse=True):
        ratio = (float(count) / total_rows * 100.0) if total_rows else 0.0
        label_rows.append([label, str(int(count)), f"{ratio:.2f}%"])

    source_rows: list[list[str]] = []
    for source_name, stats in source_stats.items():
        source_rows.append(
            [
                source_name,
                str(int(stats.get("rows_raw", 0))),
                str(int(stats.get("rows_built", 0))),
                str(int(stats.get("columns_raw", 0))),
            ]
        )

    notes = summary.get("notes", [])
    note_lines = "\n".join([f"- {n}" for n in notes]) if notes else "- (none)"

    section_lines = [
        "## Dataset Summary",
        f"- Total rows: `{total_rows}`",
        f"- Split sizes: train `{split_sizes.get('train', '-')}`, val `{split_sizes.get('val', '-')}`, test `{split_sizes.get('test', '-')}`",
        "",
        "### Label Distribution",
        table(["label", "count", "ratio"], label_rows),
        "",
        "### Source Composition",
        table(["source", "rows_raw", "rows_built", "columns_raw"], source_rows),
        "",
        "### Notes",
        note_lines,
    ]
    return "\n".join(section_lines)


def build_best_model_section(best_row: pd.Series, best_metrics: dict, metric: str) -> str:
    test_obj = best_metrics.get("test", {})
    labels = list(test_obj.get("labels", ["low", "medium", "high"]))
    report = test_obj.get("classification_report", {})
    confusion = test_obj.get("confusion_matrix", [])

    class_rows: list[list[str]] = []
    for label in labels:
        entry = report.get(label, {})
        class_rows.append(
            [
                label,
                format_float(entry.get("precision")),
                format_float(entry.get("recall")),
                format_float(entry.get("f1-score")),
                str(int(entry.get("support", 0))),
            ]
        )

    lines = [
        "## Best Model",
        f"- Selected run: `{best_row['run_name']}`",
        f"- Model type: `{best_row['model']}`",
        f"- Selection metric: `{metric}` = `{format_float(best_row.get(metric))}`",
        f"- Test accuracy: `{format_float(test_obj.get('accuracy'))}`",
        f"- Test macro F1: `{format_float(test_obj.get('macro_f1'))}`",
        f"- Test balanced accuracy: `{format_float(test_obj.get('balanced_accuracy'))}`",
        "",
        "### Per-Class Test Metrics",
        table(["label", "precision", "recall", "f1", "support"], class_rows),
    ]

    if confusion and labels:
        lines.extend(
            [
                "",
                "### Test Confusion Matrix",
                confusion_to_markdown(confusion, labels),
            ]
        )
        confusions = top_confusions(confusion, labels, k=3)
        if confusions:
            lines.append("")
            lines.append("### Top Misclassifications")
            lines.extend([f"- `{a}` -> `{p}`: `{c}` samples" for a, p, c in confusions])

    lines.extend(
        [
            "",
            "## Limitations",
            "- Public datasets are merged from different schemas and collection contexts.",
            "- Labels are partly rule-derived proxies, not clinically verified longitudinal outcomes.",
            "- This baseline validates engineering feasibility; it does not prove 1-2 month future-risk prediction in production.",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate markdown experiment report from risk-model outputs.")
    parser.add_argument("--dataset-summary", default="outputs/dataset_summary.json")
    parser.add_argument("--run-summary", default="outputs/training_runs/run_summary.csv")
    parser.add_argument("--run-dir", default="outputs/training_runs")
    parser.add_argument("--metric", default="test_macro_f1", choices=SUPPORTED_METRICS)
    parser.add_argument("--out", default="outputs/reports/experiment_report.md")
    args = parser.parse_args()

    dataset_summary_path = Path(args.dataset_summary).resolve()
    run_summary_path = Path(args.run_summary).resolve()
    run_dir = Path(args.run_dir).resolve()
    out_path = Path(args.out).resolve()

    dataset_summary = load_json(dataset_summary_path)
    if not run_summary_path.exists():
        raise FileNotFoundError(f"Missing file: {run_summary_path}")
    run_summary_df = pd.read_csv(run_summary_path)
    if run_summary_df.empty:
        raise ValueError(f"Run summary is empty: {run_summary_path}")

    best_row = select_best_run(run_summary_df, args.metric)
    best_run_name = str(best_row["run_name"])
    best_metrics_path = run_dir / best_run_name / "metrics.json"
    best_metrics = load_json(best_metrics_path)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Risk Model Baseline Experiment Report",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Dataset summary: `{dataset_summary_path}`",
        f"- Run summary: `{run_summary_path}`",
        "",
        build_dataset_section(dataset_summary),
        "",
        "## Model Comparison",
        build_model_comparison(run_summary_df),
        "",
        build_best_model_section(best_row, best_metrics, args.metric),
        "",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved report: {out_path}")
    print(f"Best run: {best_run_name} ({args.metric}={format_float(best_row.get(args.metric))})")


if __name__ == "__main__":
    main()
