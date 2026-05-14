#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
# （实验结果汇总）：
# 用于在多次模型训练（跑了不同的算法或参数）后，读取并汇总所有存放在 outputs/training_runs/ 下的训练日志和性能指标（metrics），
# 方便开发者直观地对比哪次实验的效果最好。

def main():
    parser = argparse.ArgumentParser(description="Summarize training run metrics into a single table.")
    parser.add_argument(
        "--run-dir",
        default="outputs/training_runs",
        help="Directory containing <model>_<timestamp>/metrics.json",
    )
    parser.add_argument(
        "--out",
        default="outputs/training_runs/run_summary.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    rows = []
    for sub in sorted(run_dir.glob("*")):
        metrics_path = sub / "metrics.json"
        if not metrics_path.exists():
            continue
        obj = json.loads(metrics_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "run_name": sub.name,
                "model": obj.get("model"),
                "train_rows": obj.get("train_rows"),
                "val_rows": obj.get("val_rows"),
                "test_rows": obj.get("test_rows"),
                "val_accuracy": obj.get("val", {}).get("accuracy"),
                "val_macro_f1": obj.get("val", {}).get("macro_f1"),
                "test_accuracy": obj.get("test", {}).get("accuracy"),
                "test_macro_f1": obj.get("test", {}).get("macro_f1"),
                "test_balanced_accuracy": obj.get("test", {}).get("balanced_accuracy"),
            }
        )

    if not rows:
        raise SystemExit(f"No metrics.json found under {run_dir}")

    df = pd.DataFrame(rows).sort_values(by=["test_macro_f1", "test_accuracy"], ascending=False)
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(df.to_string(index=False))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
