#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


DEFAULT_FEATURES = [
    "age",
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
    "gender",
]


# Optional aliases so existing backend payload fields can map without hard rename.
ALIASES = {
    "academicPressure": "academic_pressure",
    "workPressure": "work_pressure",
    "studySatisfaction": "study_satisfaction",
    "sleepQuality": "sleep_quality",
    "dietaryHabits": "dietary_habits",
    "anxietySignal": "anxiety_signal",
    "depressionSignal": "depression_signal",
    "panicSignal": "panic_signal",
    "socialSupport": "social_support",
    "peerPressure": "peer_pressure",
    "financialStress": "financial_stress",
    "familyHistoryMentalIllness": "family_history_mental_illness",
    "suicidalIdeation": "suicidal_ideation",
}


DIMENSION_ALIASES = {
    "anxiety": ["anxiety", "phobic", "paranoid", "hostility"],
    "depression": ["depression", "additional", "psychoticism"],
    "sleep": ["sleep"],
    "social": ["social", "interpersonal"],
    "somatic": ["somatic", "somatization"],
    "stress_related": ["compulsive"],
    "academic_pressure": ["academic_pressure", "study", "study_load"],
    "work_pressure": ["work_pressure", "work"],
    "financial_stress": ["financial_stress", "finance", "economic"],
}


def normalize_gender(value: Any) -> str:
    if value is None:
        return "unknown"
    s = str(value).strip().lower()
    if s in {"male", "m", "man"}:
        return "male"
    if s in {"female", "f", "woman"}:
        return "female"
    if s in {"unknown", ""}:
        return "unknown"
    return "other"


def to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def to_binary_flag(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y"}:
        return 1.0
    if s in {"0", "false", "no", "n"}:
        return 0.0
    f = to_float_or_none(value)
    if f is None:
        return None
    return 1.0 if f >= 0.5 else 0.0


def clamp(value: float | None, lo: float, hi: float) -> float | None:
    if value is None:
        return None
    return max(lo, min(hi, float(value)))


def invert_symptom_score(value: float | None, low: float = 1.0, high: float = 5.0) -> float | None:
    if value is None:
        return None
    v = clamp(value, low, high)
    if v is None:
        return None
    return low + high - v


class RiskPredictorAdapter:
    """
    Thin adapter for plugging exported baseline model into Django service code.
    """

    def __init__(self, model_path: str | Path, meta_path: str | Path | None = None):
        self.model_path = Path(model_path).resolve()
        self.meta_path = Path(meta_path).resolve() if meta_path else None
        self.model = joblib.load(self.model_path)
        self.feature_columns = self._resolve_feature_columns()

    def _resolve_feature_columns(self) -> list[str]:
        if self.meta_path and self.meta_path.exists():
            obj = json.loads(self.meta_path.read_text(encoding="utf-8"))
            features = obj.get("features")
            if isinstance(features, list) and features:
                return [str(x) for x in features]
        return list(DEFAULT_FEATURES)

    def _canonicalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        canonical = dict(payload)
        for old, new in ALIASES.items():
            if old in canonical and new not in canonical:
                canonical[new] = canonical[old]
        return canonical

    def _build_input_frame(self, payload: dict[str, Any]) -> pd.DataFrame:
        canonical = self._canonicalize_payload(payload)
        row: dict[str, Any] = {}
        for col in self.feature_columns:
            raw = canonical.get(col)
            if col == "gender":
                row[col] = normalize_gender(raw)
            else:
                row[col] = to_float_or_none(raw)
        return pd.DataFrame([row], columns=self.feature_columns)

    @staticmethod
    def _mean_available(values: list[float | None]) -> float | None:
        existing = [float(v) for v in values if v is not None]
        if not existing:
            return None
        return sum(existing) / len(existing)

    def _read_dim(self, dim_scores: dict[str, Any], alias_key: str) -> float | None:
        aliases = DIMENSION_ALIASES.get(alias_key, [alias_key])
        values: list[float | None] = []
        for key in aliases:
            values.append(to_float_or_none(dim_scores.get(key)))
        return self._mean_available(values)

    def build_payload_from_assessment_scores(
        self,
        *,
        avg_score: float,
        dim_scores: dict[str, Any],
        student_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Convert existing backend assessment inputs (avg + dimensions) into
        model feature payload with best-effort heuristics.
        """
        profile = student_profile or {}
        avg = clamp(to_float_or_none(avg_score), 1.0, 5.0)
        anxiety = clamp(self._read_dim(dim_scores, "anxiety"), 1.0, 5.0)
        depression = clamp(self._read_dim(dim_scores, "depression"), 1.0, 5.0)
        sleep_symptom = clamp(self._read_dim(dim_scores, "sleep"), 1.0, 5.0)
        social_symptom = clamp(self._read_dim(dim_scores, "social"), 1.0, 5.0)
        somatic = clamp(self._read_dim(dim_scores, "somatic"), 1.0, 5.0)
        academic_pressure = clamp(self._read_dim(dim_scores, "academic_pressure"), 1.0, 5.0)
        work_pressure = clamp(self._read_dim(dim_scores, "work_pressure"), 1.0, 5.0)
        financial_stress = clamp(self._read_dim(dim_scores, "financial_stress"), 1.0, 5.0)

        # If questionnaire does not expose dedicated dimensions, fallback to avg severity.
        if academic_pressure is None:
            academic_pressure = avg
        if work_pressure is None:
            work_pressure = avg if avg is not None and avg >= 3.0 else None
        if financial_stress is None:
            financial_stress = avg

        payload = {
            "age": to_float_or_none(profile.get("age")),
            "gender": profile.get("gender"),
            "cgpa": to_float_or_none(profile.get("cgpa")),
            "academic_pressure": academic_pressure,
            "work_pressure": work_pressure,
            "study_satisfaction": invert_symptom_score(avg),
            "sleep_quality": invert_symptom_score(sleep_symptom),
            "dietary_habits": invert_symptom_score(somatic) if somatic is not None else None,
            "anxiety_signal": 1.0 if anxiety is not None and anxiety >= 3.0 else (0.0 if anxiety is not None else None),
            "depression_signal": (
                1.0 if depression is not None and depression >= 3.0 else (0.0 if depression is not None else None)
            ),
            "panic_signal": (
                1.0
                if anxiety is not None and depression is not None and anxiety >= 4.0 and depression >= 4.0
                else (0.0 if anxiety is not None or depression is not None else None)
            ),
            "social_support": invert_symptom_score(social_symptom),
            "peer_pressure": social_symptom,
            "financial_stress": financial_stress,
            "family_history_mental_illness": to_binary_flag(profile.get("family_history_mental_illness")),
            "suicidal_ideation": to_binary_flag(profile.get("suicidal_ideation")),
        }
        return payload

    def predict_one(self, payload: dict[str, Any]) -> dict[str, Any]:
        x = self._build_input_frame(payload)
        label = str(self.model.predict(x)[0])
        result: dict[str, Any] = {"label": label}

        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(x)[0]
            classes = list(getattr(self.model, "classes_", []))
            result["probabilities"] = {str(c): float(p) for c, p in zip(classes, proba)}

        return result

    def predict_from_assessment_scores(
        self,
        *,
        avg_score: float,
        dim_scores: dict[str, Any],
        student_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self.build_payload_from_assessment_scores(
            avg_score=avg_score,
            dim_scores=dim_scores,
            student_profile=student_profile,
        )
        result = self.predict_one(payload)
        result["payload_used"] = payload
        return result


def main():
    parser = argparse.ArgumentParser(description="Run one-off prediction from JSON payload (adapter smoke test).")
    parser.add_argument("--model", required=True, help="Path to exported model.joblib")
    parser.add_argument("--meta", default="", help="Optional path to model_meta.json")
    parser.add_argument("--payload", default="", help="JSON object string for one sample (direct feature payload)")
    parser.add_argument("--avg-score", type=float, default=None, help="Assessment avg score (1-5)")
    parser.add_argument("--dim-scores", default="", help="JSON object for dimension scores, e.g. {\"anxiety\":3.2}")
    parser.add_argument("--student-profile", default="", help="Optional JSON object with age/gender/cgpa/etc.")
    args = parser.parse_args()

    meta = args.meta or None
    adapter = RiskPredictorAdapter(model_path=args.model, meta_path=meta)
    if args.payload:
        payload = json.loads(args.payload)
        result = adapter.predict_one(payload)
    else:
        if args.avg_score is None or not args.dim_scores:
            raise SystemExit(
                "Either provide --payload, or provide both --avg-score and --dim-scores."
            )
        dim_scores = json.loads(args.dim_scores)
        student_profile = json.loads(args.student_profile) if args.student_profile else None
        result = adapter.predict_from_assessment_scores(
            avg_score=args.avg_score,
            dim_scores=dim_scores,
            student_profile=student_profile,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
