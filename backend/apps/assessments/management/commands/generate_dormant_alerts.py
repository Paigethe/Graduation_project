from django.core.management.base import BaseCommand

from apps.assessments.services import ensure_dormant_high_risk_alerts


class Command(BaseCommand):
    help = "生成高风险学生长期未登录预警"

    def handle(self, *args, **options):
        created = ensure_dormant_high_risk_alerts()
        self.stdout.write(self.style.SUCCESS(f"生成预警 {created} 条"))

