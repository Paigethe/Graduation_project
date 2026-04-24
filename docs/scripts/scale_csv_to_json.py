import csv
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scale_csv_to_json.py <csv_path> <json_out> [--name <name>] [--scale_type <type>] [--desc <desc>]")
        return 1

    csv_path = Path(sys.argv[1]).expanduser().resolve()
    out_path = Path(sys.argv[2]).expanduser().resolve()

    name = "SCL-90 标准量表"
    scale_type = "custom"
    desc = ""
    if "--name" in sys.argv:
        name = sys.argv[sys.argv.index("--name") + 1]
    if "--scale_type" in sys.argv:
        scale_type = sys.argv[sys.argv.index("--scale_type") + 1]
    if "--desc" in sys.argv:
        desc = sys.argv[sys.argv.index("--desc") + 1]

    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 1

    questions = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("id") or not row.get("text"):
                continue
            questions.append(
                {
                    "id": int(row["id"]),
                    "text": row["text"],
                    "dimension": row.get("dimension") or "overall",
                    "weight": float(row.get("weight") or 1),
                    "min": int(row.get("min") or 1),
                    "max": int(row.get("max") or 5),
                }
            )

    payload = {
        "name": name,
        "scale_type": scale_type,
        "description": desc,
        "questions": questions,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
