#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
# （离线批量预测工具）：
# 一个便捷的测试脚本。允许你不启动 Django 后端，直接读取本地包含学生特征的 CSV 文件，加载导出的模型进行批量风险预测，
# 主要用于离线验证模型的推理效果是否符合预期

def main():
    parser = argparse.ArgumentParser(description="Run inference on CSV with a trained baseline model.")
    parser.add_argument("--model", required=True, help="Path to model.joblib")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", required=True, help="Output CSV path with predictions")
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = joblib.load(model_path)
    df = pd.read_csv(input_path)

    # Keep behavior simple: if labels exist, keep them; prediction ignores y columns.
    drop_cols = [c for c in ["y_risk", "y_risk_id"] if c in df.columns]
    x = df.drop(columns=drop_cols, errors="ignore")

    pred = model.predict(x)
    out = df.copy()
    out["y_pred"] = pred

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x)
        classes = list(getattr(model, "classes_", []))
        for i, cls in enumerate(classes):
            out[f"proba_{cls}"] = proba[:, i]

    out.to_csv(output_path, index=False)
    print(f"Saved predictions: {output_path}")
    print(f"rows={len(out)}")


if __name__ == "__main__":
    main()
