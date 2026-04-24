from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgearticle",
            name="document",
            field=models.FileField(blank=True, null=True, upload_to="knowledge_docs/"),
        ),
    ]
