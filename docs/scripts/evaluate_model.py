import csv
import json
import sys
from collections import Counter


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python evaluate_model.py <csv_path> [--out result.json]")
        return 1

    csv_path = sys.argv[1]
    out_path = None
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        if idx + 1 < len(sys.argv):
            out_path = sys.argv[idx + 1]

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        print("No rows found.")
        return 1

    y_true = [r.get("y_true") for r in rows]
    y_pred = [r.get("y_pred") for r in rows]
    total = len(rows)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    acc = correct / total if total else 0.0

    label_counts = Counter(y_true)
    pred_counts = Counter(y_pred)

    result = {
        "total": total,
        "accuracy": acc,
        "label_counts": dict(label_counts),
        "pred_counts": dict(pred_counts),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
