import json

from django.core.management.base import BaseCommand
from django.db import models

from apps.assessments.models import AssessmentResult


class Command(BaseCommand):
    help = "Evaluate predicted_risk_level vs risk_level (baseline)."

    def add_arguments(self, parser):
        parser.add_argument("--out", type=str, default=None, help="Output JSON file path")

    def handle(self, *args, **options):
        qs = AssessmentResult.objects.all()
        total = qs.count()
        correct = qs.filter(risk_level=models.F("predicted_risk_level")).count()
        acc = (correct / total) if total else 0.0

        by_level = {
            "low": qs.filter(risk_level="low").count(),
            "medium": qs.filter(risk_level="medium").count(),
            "high": qs.filter(risk_level="high").count(),
        }

        result = {
            "total": total,
            "accuracy": acc,
            "by_level": by_level,
            "note": "Baseline: risk_level vs predicted_risk_level (not expert labels).",
        }

        payload = json.dumps(result, ensure_ascii=False, indent=2)
        self.stdout.write(payload)

        out_path = options.get("out")
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(payload)
