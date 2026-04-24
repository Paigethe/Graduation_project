from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Major",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "college",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="majors",
                        to="accounts.college",
                    ),
                ),
            ],
            options={
                "verbose_name": "专业",
                "verbose_name_plural": "专业",
                "ordering": ["college_id", "name", "id"],
            },
        ),
        migrations.CreateModel(
            name="ClassGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "major",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="classes",
                        to="accounts.major",
                    ),
                ),
            ],
            options={
                "verbose_name": "班级",
                "verbose_name_plural": "班级",
                "ordering": ["major_id", "name", "id"],
            },
        ),
        migrations.AddField(
            model_name="user",
            name="major",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users",
                to="accounts.major",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="class_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="students",
                to="accounts.classgroup",
            ),
        ),
        migrations.CreateModel(
            name="CounselorClassAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "class_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assigned_counselors",
                        to="accounts.classgroup",
                    ),
                ),
                (
                    "counselor",
                    models.ForeignKey(
                        limit_choices_to={"role": "counselor"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assigned_classes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "班级咨询分配",
                "verbose_name_plural": "班级咨询分配",
            },
        ),
        migrations.AddConstraint(
            model_name="major",
            constraint=models.UniqueConstraint(fields=("college", "name"), name="uniq_major_college_name"),
        ),
        migrations.AddConstraint(
            model_name="classgroup",
            constraint=models.UniqueConstraint(fields=("major", "name"), name="uniq_class_major_name"),
        ),
        migrations.AddConstraint(
            model_name="counselorclassassignment",
            constraint=models.UniqueConstraint(fields=("counselor", "class_group"), name="uniq_counselor_class"),
        ),
        migrations.AddConstraint(
            model_name="counselorclassassignment",
            constraint=models.UniqueConstraint(fields=("class_group",), name="uniq_class_one_counselor"),
        ),
    ]
