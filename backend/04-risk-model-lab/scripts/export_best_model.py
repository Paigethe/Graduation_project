#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
# 最优模型导出交付）：
# 它是连接“实验室”与“真实业务”的桥梁。负责将综合评估表现最好的模型通过 joblib 库进行序列化打包导出，
# 同时生成包含模型版本等信息的元数据文件（model_meta.json），最终输出到 artifacts/best_model/ 目录下，供 Django 后端线上系统（predictor.py）直接加载调用。
def main():
    parser = argparse.ArgumentParser(description="Select and export the best training run.")
    parser.add_argument(
        "--run-summary",
        default="outputs/training_runs/run_summary.csv",
        help="Path to run_summary.csv",
    )
    parser.add_argument(
        "--run-dir",
        default="outputs/training_runs",
        help="Directory containing training run subfolders",
    )
    parser.add_argument(
        "--metric",
        default="test_macro_f1",
        choices=["test_macro_f1", "test_accuracy", "test_balanced_accuracy"],
        help="Primary metric used for selecting the best run",
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts/best_model",
        help="Output directory for exported best model",
    )
    args = parser.parse_args()

    summary_path = Path(args.run_summary).resolve()
    run_dir = Path(args.run_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary file: {summary_path}")

    df = pd.read_csv(summary_path)
    if args.metric not in df.columns:
        raise ValueError(f"Metric '{args.metric}' not found in summary columns: {list(df.columns)}")

    sort_cols = [args.metric]
    if "test_accuracy" in df.columns and args.metric != "test_accuracy":
        sort_cols.append("test_accuracy")
    if "val_macro_f1" in df.columns:
        sort_cols.append("val_macro_f1")

    best = df.sort_values(by=sort_cols, ascending=False).iloc[0].to_dict()
    best_run_name = str(best["run_name"])
    best_run_dir = run_dir / best_run_name
    if not best_run_dir.exists():
        raise FileNotFoundError(f"Best run directory not found: {best_run_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    for fname in [
        "model.joblib",
        "model_meta.json",
        "metrics.json",
        "confusion_val.csv",
        "confusion_test.csv",
        "test_predictions.csv",
    ]:
        src = best_run_dir / fname
        if src.exists():
            shutil.copy2(src, out_dir / fname)

    manifest = {
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_metric": args.metric,
        "best_run": best,
        "source_run_dir": str(best_run_dir),
        "export_dir": str(out_dir),
    }
    manifest_path = out_dir / "best_model_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Best run: {best_run_name}")
    print(f"Metric ({args.metric}): {best[args.metric]}")
    print(f"Exported to: {out_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
