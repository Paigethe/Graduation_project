from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0002_article_document"),
        ("interventions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="interventionplan",
            name="knowledge_article",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="intervention_plans",
                to="knowledge.knowledgearticle",
            ),
        ),
        migrations.AlterField(
            model_name="interventionplan",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "草稿"),
                    ("sent", "已推送"),
                    ("in_progress", "进行中"),
                    ("done", "已完成"),
                ],
                default="in_progress",
                max_length=20,
            ),
        ),
    ]
