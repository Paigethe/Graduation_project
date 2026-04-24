from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentresult",
            name="model_meta",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
