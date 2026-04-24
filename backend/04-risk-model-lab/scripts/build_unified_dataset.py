#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import requests


@dataclass(frozen=True)
class DatasetSpec:
    source_name: str
    kaggle_slug: str
    file_name: str
    builder: Callable[[pd.DataFrame], pd.DataFrame]


TARGET_COLUMNS = [
    "source_dataset",
    "source_row_id",
    "age",
    "gender",
    "cgpa",
    "academic_pressure",
    "work_pressure",
    "study_satisfaction",
    "sleep_quality",
    "dietary_habits",
    "anxiety_signal",
    "depression_signal",
    "panic_signal",
    "social_support",
    "peer_pressure",
    "financial_stress",
    "family_history_mental_illness",
    "suicidal_ideation",
    "y_risk",
    "y_risk_id",
]


RISK_TO_ID = {"low": 0, "medium": 1, "high": 2}


def to_float(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def yn_to_int(value) -> int | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in {"yes", "y", "1", "true"}:
        return 1
    if s in {"no", "n", "0", "false"}:
        return 0
    return None


def normalize_gender(value: str | None) -> str:
    if value is None:
        return "unknown"
    s = str(value).strip().lower()
    if s in {"male", "m", "man"}:
        return "male"
    if s in {"female", "f", "woman"}:
        return "female"
    return "other"


def parse_cgpa(value) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # examples: "3.00 - 3.49", "3.75"
    if "-" in s:
        parts = [p.strip() for p in s.replace("–", "-").split("-")]
        nums = [to_float(p) for p in parts]
        nums = [n for n in nums if n is not None]
        if len(nums) == 2:
            return (nums[0] + nums[1]) / 2.0
    return to_float(s)


def encode_sleep_duration_to_quality(value) -> float | None:
    # Maps textual sleep duration to a rough quality score (1~5).
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    if "less than 5" in s or "<5" in s:
        return 1.0
    if "5-6" in s or "5 to 6" in s:
        return 2.0
    if "6-7" in s or "6 to 7" in s:
        return 3.0
    if "7-8" in s or "7 to 8" in s:
        return 4.0
    if "more than 8" in s or ">8" in s or "8+" in s:
        return 3.0
    # If numeric hours appear, use simple rule.
    num = to_float(s)
    if num is None:
        return None
    if num < 5:
        return 1.0
    if num < 6:
        return 2.0
    if num < 7:
        return 3.0
    if num <= 8:
        return 4.0
    return 3.0


def encode_dietary_habits(value) -> float | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    if "healthy" in s:
        return 2.0
    if "moderate" in s:
        return 1.0
    if "unhealthy" in s:
        return 0.0
    return None


def map_risk_id(label: str) -> int:
    return RISK_TO_ID[label]


def risk_from_dep_with_rules(
    depression_signal: int | None,
    suicidal_ideation: int | None,
    financial_stress: float | None,
    academic_pressure: float | None,
    work_pressure: float | None,
) -> str:
    dep = int(depression_signal or 0)
    if dep == 0:
        return "low"
    high = (
        (suicidal_ideation or 0) == 1
        or (financial_stress is not None and financial_stress >= 4)
        or (academic_pressure is not None and academic_pressure >= 4)
        or (work_pressure is not None and work_pressure >= 4)
    )
    if high:
        return "high"
    return "medium"


def risk_from_dep_anx_panic(dep: int | None, anx: int | None, panic: int | None) -> str:
    score = int(dep or 0) + int(anx or 0) + int(panic or 0)
    if score <= 0:
        return "low"
    if score == 1:
        return "medium"
    return "high"


def build_from_adil(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["source_dataset"] = "adilshamim8/student-depression-dataset"
    out["source_row_id"] = df.get("id")
    out["age"] = df.get("Age").map(to_float)
    out["gender"] = df.get("Gender").map(normalize_gender)
    out["cgpa"] = df.get("CGPA").map(parse_cgpa)
    out["academic_pressure"] = df.get("Academic Pressure").map(to_float)
    out["work_pressure"] = df.get("Work Pressure").map(to_float)
    out["study_satisfaction"] = df.get("Study Satisfaction").map(to_float)
    out["sleep_quality"] = df.get("Sleep Duration").map(encode_sleep_duration_to_quality)
    out["dietary_habits"] = df.get("Dietary Habits").map(encode_dietary_habits)
    out["anxiety_signal"] = None
    out["depression_signal"] = df.get("Depression").map(to_float).fillna(0).astype(int)
    out["panic_signal"] = None
    out["social_support"] = None
    out["peer_pressure"] = None
    out["financial_stress"] = df.get("Financial Stress").map(to_float)
    out["family_history_mental_illness"] = df.get("Family History of Mental Illness").map(yn_to_int)
    out["suicidal_ideation"] = df.get("Have you ever had suicidal thoughts ?").map(yn_to_int)
    out["y_risk"] = out.apply(
        lambda r: risk_from_dep_with_rules(
            r["depression_signal"],
            r["suicidal_ideation"],
            r["financial_stress"],
            r["academic_pressure"],
            r["work_pressure"],
        ),
        axis=1,
    )
    out["y_risk_id"] = out["y_risk"].map(map_risk_id)
    return out[TARGET_COLUMNS]


def build_from_stress_monitoring(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["source_dataset"] = "mdsultanulislamovi/student-stress-monitoring-datasets"
    out["source_row_id"] = df.index
    out["age"] = None
    out["gender"] = "unknown"
    out["cgpa"] = df.get("academic_performance").map(to_float)
    out["academic_pressure"] = df.get("study_load").map(to_float)
    out["work_pressure"] = None
    out["study_satisfaction"] = None
    out["sleep_quality"] = df.get("sleep_quality").map(to_float)
    out["dietary_habits"] = None
    out["anxiety_signal"] = df.get("anxiety_level").map(to_float)
    out["depression_signal"] = df.get("depression").map(to_float)
    out["panic_signal"] = None
    out["social_support"] = df.get("social_support").map(to_float)
    out["peer_pressure"] = df.get("peer_pressure").map(to_float)
    out["financial_stress"] = None
    out["family_history_mental_illness"] = df.get("mental_health_history").map(to_float)
    out["suicidal_ideation"] = None

    # stress_level expected 0/1/2
    out["y_risk_id"] = df.get("stress_level").map(to_float).fillna(1).astype(int)
    id_to_risk = {0: "low", 1: "medium", 2: "high"}
    out["y_risk"] = out["y_risk_id"].map(id_to_risk).fillna("medium")
    return out[TARGET_COLUMNS]


def build_from_shariful(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["source_dataset"] = "shariful07/student-mental-health"
    out["source_row_id"] = df.index
    out["age"] = df.get("Age").map(to_float)
    out["gender"] = df.get("Choose your gender").map(normalize_gender)
    out["cgpa"] = df.get("What is your CGPA?").map(parse_cgpa)
    out["academic_pressure"] = None
    out["work_pressure"] = None
    out["study_satisfaction"] = None
    out["sleep_quality"] = None
    out["dietary_habits"] = None
    out["anxiety_signal"] = df.get("Do you have Anxiety?").map(yn_to_int)
    out["depression_signal"] = df.get("Do you have Depression?").map(yn_to_int)
    out["panic_signal"] = df.get("Do you have Panic attack?").map(yn_to_int)
    out["social_support"] = None
    out["peer_pressure"] = None
    out["financial_stress"] = None
    out["family_history_mental_illness"] = None
    out["suicidal_ideation"] = None
    out["y_risk"] = out.apply(
        lambda r: risk_from_dep_anx_panic(
            r["depression_signal"],
            r["anxiety_signal"],
            r["panic_signal"],
        ),
        axis=1,
    )
    out["y_risk_id"] = out["y_risk"].map(map_risk_id)
    return out[TARGET_COLUMNS]


SPECS = [
    DatasetSpec(
        source_name="adil_student_depression",
        kaggle_slug="adilshamim8/student-depression-dataset",
        file_name="student_depression_dataset.csv",
        builder=build_from_adil,
    ),
    DatasetSpec(
        source_name="stress_monitoring",
        kaggle_slug="mdsultanulislamovi/student-stress-monitoring-datasets",
        file_name="StressLevelDataset.csv",
        builder=build_from_stress_monitoring,
    ),
    DatasetSpec(
        source_name="student_mental_health_small",
        kaggle_slug="shariful07/student-mental-health",
        file_name="Student Mental health.csv",
        builder=build_from_shariful,
    ),
]


def download_kaggle_file(slug: str, file_name: str, out_path: Path, force_download: bool) -> Path:
    if out_path.exists() and not force_download:
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://www.kaggle.com/api/v1/datasets/download/{slug}/{file_name}"
    resp = requests.get(url, timeout=40, allow_redirects=False)
    if resp.status_code != 302:
        raise RuntimeError(
            f"Failed to get signed URL for {slug}/{file_name}. "
            f"Status={resp.status_code}, body={resp.text[:160]}"
        )
    signed_url = resp.headers.get("Location")
    if not signed_url:
        raise RuntimeError(f"Signed URL missing for {slug}/{file_name}")

    file_resp = requests.get(signed_url, timeout=120)
    if file_resp.status_code != 200:
        raise RuntimeError(
            f"Download failed for {slug}/{file_name}. "
            f"Status={file_resp.status_code}"
        )
    out_path.write_bytes(file_resp.content)
    return out_path


def impute_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    numeric_cols = [
        c
        for c in out.columns
        if c not in {"source_dataset", "source_row_id", "gender", "y_risk"}
    ]
    for col in numeric_cols:
        series = pd.to_numeric(out[col], errors="coerce")
        med = series.median()
        if pd.notna(med):
            out[col] = series.fillna(med)
        else:
            out[col] = series
    return out


def stratified_split(
    df: pd.DataFrame,
    label_col: str,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_parts = []
    val_parts = []
    test_parts = []

    for _label, group in df.groupby(label_col):
        g = group.sample(frac=1.0, random_state=seed)
        n = len(g)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        train_parts.append(g.iloc[:n_train])
        val_parts.append(g.iloc[n_train : n_train + n_val])
        test_parts.append(g.iloc[n_train + n_val :])

    train_df = pd.concat(train_parts).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    val_df = pd.concat(val_parts).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    test_df = pd.concat(test_parts).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return train_df, val_df, test_df


def main():
    parser = argparse.ArgumentParser(
        description="Build unified student risk dataset from selected Kaggle datasets."
    )
    parser.add_argument("--cache-dir", default="cache", help="Directory to cache raw downloaded CSV files.")
    parser.add_argument("--out-dir", default="outputs", help="Directory to write merged dataset outputs.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for split.")
    parser.add_argument("--force-download", action="store_true", help="Re-download even if cache file exists.")
    parser.add_argument("--impute", action="store_true", help="Median-impute missing numeric values.")
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    built_frames = []
    source_stats = {}

    for spec in SPECS:
        cache_path = cache_dir / f"{spec.source_name}.csv"
        print(f"[download] {spec.kaggle_slug}/{spec.file_name}")
        csv_path = download_kaggle_file(
            slug=spec.kaggle_slug,
            file_name=spec.file_name,
            out_path=cache_path,
            force_download=args.force_download,
        )
        raw = pd.read_csv(csv_path)
        built = spec.builder(raw)
        built_frames.append(built)
        source_stats[spec.source_name] = {
            "rows_raw": int(len(raw)),
            "rows_built": int(len(built)),
            "columns_raw": int(len(raw.columns)),
        }
        print(
            f"[ok] {spec.source_name}: raw={len(raw)} rows -> built={len(built)} rows"
        )

    # Drop per-source all-NA columns before concat to avoid pandas future warnings,
    # then restore the target schema after merge.
    merged = pd.concat(
        [frame.dropna(axis=1, how="all") for frame in built_frames],
        ignore_index=True,
        sort=False,
    )
    merged = merged.reindex(columns=TARGET_COLUMNS)
    if args.impute:
        merged = impute_numeric_columns(merged)

    # Ensure label integrity
    merged["y_risk"] = merged["y_risk"].fillna("medium")
    merged["y_risk_id"] = merged["y_risk"].map(RISK_TO_ID).fillna(1).astype(int)

    merged_path = out_dir / "unified_student_risk_dataset.csv"
    merged.to_csv(merged_path, index=False)

    train_df, val_df, test_df = stratified_split(merged, label_col="y_risk", seed=args.seed)
    train_path = out_dir / "train.csv"
    val_path = out_dir / "val.csv"
    test_path = out_dir / "test.csv"
    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)

    summary = {
        "total_rows": int(len(merged)),
        "columns": list(merged.columns),
        "label_distribution": merged["y_risk"].value_counts(dropna=False).to_dict(),
        "split_sizes": {
            "train": int(len(train_df)),
            "val": int(len(val_df)),
            "test": int(len(test_df)),
        },
        "source_stats": source_stats,
        "notes": [
            "This unified dataset is intended for baseline risk classification.",
            "It is not longitudinal ground-truth for future 1-2 month risk prediction.",
        ],
    }
    summary_path = out_dir / "dataset_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Done ===")
    print(f"merged: {merged_path}")
    print(f"train : {train_path}")
    print(f"val   : {val_path}")
    print(f"test  : {test_path}")
    print(f"summary: {summary_path}")
    print(f"label distribution: {summary['label_distribution']}")


if __name__ == "__main__":
    main()
