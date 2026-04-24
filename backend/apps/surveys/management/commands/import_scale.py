import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.surveys.models import QuestionnaireTemplate


class Command(BaseCommand):
    help = "Import questionnaire template from JSON file."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to scale template JSON")
        parser.add_argument("--update", action="store_true", help="Update existing template if name exists")

    def handle(self, *args, **options):
        file_path = Path(options["file"]).expanduser().resolve()
        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        raw = json.loads(file_path.read_text(encoding="utf-8"))
        name = str(raw.get("name") or "").strip()
        scale_type = str(raw.get("scale_type") or "custom").strip()
        description = str(raw.get("description") or "").strip()
        questions = raw.get("questions") or []

        if not name:
            self.stderr.write(self.style.ERROR("Missing name in JSON"))
            return
        if not isinstance(questions, list) or not questions:
            self.stderr.write(self.style.ERROR("Questions must be a non-empty list"))
            return

        # Normalize scale_type to valid choices
        valid = {c[0] for c in QuestionnaireTemplate.ScaleType.choices}
        if scale_type not in valid:
            scale_type = QuestionnaireTemplate.ScaleType.CUSTOM

        tpl = QuestionnaireTemplate.objects.filter(name=name).first()
        if tpl and not options["update"]:
            self.stderr.write(self.style.WARNING(f"Template exists: {name} (use --update to overwrite)"))
            return

        if tpl:
            tpl.scale_type = scale_type
            tpl.description = description
            tpl.questions = questions
            tpl.save(update_fields=["scale_type", "description", "questions"])
        else:
            tpl = QuestionnaireTemplate.objects.create(
                name=name,
                scale_type=scale_type,
                description=description,
                questions=questions,
            )

        self.stdout.write(self.style.SUCCESS(f"Imported template: {tpl.name}"))
