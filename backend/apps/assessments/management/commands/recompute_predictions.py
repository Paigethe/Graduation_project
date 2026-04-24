from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessments.models import AssessmentResult
from apps.assessments.predictor import predict_risk


def _extract_student_profile(assessment: AssessmentResult) -> dict[str, Any] | None:
    response = getattr(assessment, "response", None)
    answers = getattr(response, "answers", None)
    if not isinstance(answers, dict):
        return None

    canonical_map = {
        "age": "age",
        "gender": "gender",
        "cgpa": "cgpa",
        "family_history_mental_illness": "family_history_mental_illness",
        "suicidal_ideation": "suicidal_ideation",
        "familyHistoryMentalIllness": "family_history_mental_illness",
        "suicidalIdeation": "suicidal_ideation",
    }
    profile: dict[str, Any] = {}
    for raw_key, canonical in canonical_map.items():
        if raw_key in answers and canonical not in profile:
            profile[canonical] = answers.get(raw_key)
    return profile or None


class Command(BaseCommand):
    help = "Recompute predicted_risk_level/model_meta for existing assessments using current predictor."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only print planned changes, do not write.")
        parser.add_argument("--limit", type=int, default=0, help="Max records to process (0 means all).")
        parser.add_argument("--from-id", type=int, default=0, help="Process id >= from-id.")
        parser.add_argument("--to-id", type=int, default=0, help="Process id <= to-id.")
        parser.add_argument(
            "--only-mismatch",
            action="store_true",
            help="Only update rows where predicted_risk_level would change.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        limit = int(options.get("limit") or 0)
        from_id = int(options.get("from_id") or 0)
        to_id = int(options.get("to_id") or 0)
        only_mismatch = bool(options.get("only_mismatch"))

        qs = AssessmentResult.objects.select_related("response").all().order_by("id")
        if from_id > 0:
            qs = qs.filter(id__gte=from_id)
        if to_id > 0:
            qs = qs.filter(id__lte=to_id)

        total_candidates = qs.count()

        processed = 0
        updated = 0
        unchanged = 0
        failed = 0

        self.stdout.write(
            f"[start] candidates={total_candidates}, dry_run={dry_run}, limit={limit or 'all'}"
        )

        for item in qs.iterator(chunk_size=200):
            if limit > 0 and processed >= limit:
                break
            processed += 1
            try:
                dim_scores = item.dimension_scores if isinstance(item.dimension_scores, dict) else {}
                profile = _extract_student_profile(item)
                result = predict_risk(
                    avg_score=float(item.avg_score or 0.0),
                    dim_scores=dim_scores,
                    student_profile=profile,
                )

                old_pred = str(item.predicted_risk_level or "")
                new_pred = str(result.predicted_risk_level or "")
                old_meta = item.model_meta if isinstance(item.model_meta, dict) else {}
                new_meta = {
                    **old_meta,
                    "model_version": result.model_version,
                    "confidence": result.confidence,
                }
                changed = (old_pred != new_pred) or (old_meta.get("model_version") != result.model_version) or (
                    old_meta.get("confidence") != result.confidence
                )

                if only_mismatch and old_pred == new_pred:
                    unchanged += 1
                    continue

                if not changed:
                    unchanged += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f"[dry-run] id={item.id} pred: {old_pred} -> {new_pred}; "
                        f"version: {old_meta.get('model_version')} -> {result.model_version}; "
                        f"conf: {old_meta.get('confidence')} -> {result.confidence:.4f}"
                    )
                    updated += 1
                    continue

                with transaction.atomic():
                    item.predicted_risk_level = new_pred
                    item.model_meta = new_meta
                    item.save(update_fields=["predicted_risk_level", "model_meta"])
                updated += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(f"[error] id={getattr(item, 'id', '?')}: {exc}")

        self.stdout.write(
            f"[done] processed={processed}, updated={updated}, unchanged={unchanged}, failed={failed}, dry_run={dry_run}"
        )
