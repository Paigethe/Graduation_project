from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import CollegeSerializer, UserMeSerializer

from .models import Questionnaire, QuestionnaireResponse, QuestionnaireRetestTask, QuestionnaireTemplate

User = get_user_model()


class QuestionnaireTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionnaireTemplate
        fields = ["id", "name", "scale_type", "description", "questions", "created_at"]


class QuestionnaireTemplateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionnaireTemplate
        fields = ["id", "name", "scale_type", "description", "questions"]


class QuestionnaireSerializer(serializers.ModelSerializer):
    template = QuestionnaireTemplateSerializer(read_only=True)
    target_college = CollegeSerializer(read_only=True)
    created_by = UserMeSerializer(read_only=True)
    retest_pending = serializers.SerializerMethodField()

    class Meta:
        model = Questionnaire
        fields = [
            "id",
            "title",
            "description",
            "is_active",
            "start_at",
            "end_at",
            "template",
            "target_college",
            "created_by",
            "created_at",
            "retest_pending",
        ]

    def get_retest_pending(self, obj: Questionnaire) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not getattr(user, "is_student", False):
            return False
        return QuestionnaireRetestTask.objects.filter(
            questionnaire=obj,
            student=user,
            status=QuestionnaireRetestTask.Status.PENDING,
        ).exists()


class QuestionnaireCreateSerializer(serializers.ModelSerializer):
    template_id = serializers.IntegerField(write_only=True)
    target_college_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Questionnaire
        fields = [
            "id",
            "title",
            "description",
            "is_active",
            "start_at",
            "end_at",
            "template_id",
            "target_college_id",
        ]

    def validate_template_id(self, value: int) -> int:
        if not QuestionnaireTemplate.objects.filter(id=value).exists():
            raise serializers.ValidationError("无效的问卷模板")
        return value

    def create(self, validated_data):
        template = QuestionnaireTemplate.objects.get(id=validated_data.pop("template_id"))
        target_college_id = validated_data.pop("target_college_id", None)
        request = self.context["request"]
        user = request.user

        target_college = None
        if getattr(user, "is_college_admin", False):
            target_college = user.college
        elif target_college_id:
            from apps.accounts.models import College

            target_college = College.objects.filter(id=target_college_id).first()

        return Questionnaire.objects.create(
            **validated_data, template=template, target_college=target_college, created_by=user
        )


class QuestionnaireResponseSerializer(serializers.ModelSerializer):
    student = UserMeSerializer(read_only=True)

    class Meta:
        model = QuestionnaireResponse
        fields = ["id", "questionnaire", "student", "answers", "submitted_at"]
        read_only_fields = ["id", "student", "submitted_at"]


class SubmitResponseSerializer(serializers.Serializer):
    answers = serializers.DictField(child=serializers.FloatField())

    def validate_answers(self, value):
        if not isinstance(value, dict) or not value:
            raise serializers.ValidationError("answers 不能为空")
        return value

    @staticmethod
    def _to_float(value, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    def validate(self, attrs):
        questionnaire = self.context.get("questionnaire")
        if questionnaire is None:
            return attrs

        questions = (questionnaire.template.questions or []) if questionnaire.template else []
        if not questions:
            return attrs

        answers = attrs.get("answers") or {}
        normalized: dict[str, float] = {}
        expected_ids: list[str] = []
        expected_set: set[str] = set()

        errors: dict[str, list[str]] = {}
        missing: list[str] = []

        for q in questions:
            qid = str(q.get("id", "")).strip()
            if not qid:
                continue
            expected_ids.append(qid)
            expected_set.add(qid)

            raw = answers.get(qid)
            if raw is None and qid.isdigit():
                raw = answers.get(int(qid))
            if raw is None:
                missing.append(qid)
                continue

            value = self._to_float(raw, default=float("nan"))
            if value != value:  # NaN check
                errors.setdefault(qid, []).append("答案必须为数字")
                continue

            q_min = self._to_float(q.get("min", 1), 1.0)
            q_max = self._to_float(q.get("max", 5), 5.0)
            if q_max < q_min:
                q_min, q_max = q_max, q_min

            if value < q_min or value > q_max:
                errors.setdefault(qid, []).append(f"答案需在 {q_min:g}~{q_max:g} 区间内")
                continue

            normalized[qid] = value

        extras = []
        for key in answers.keys():
            key_str = str(key)
            if key_str not in expected_set:
                extras.append(key_str)

        if missing:
            errors["missing_question_ids"] = [",".join(missing)]
        if extras:
            errors["extra_question_ids"] = [",".join(extras)]
        if errors:
            raise serializers.ValidationError(errors)

        attrs["answers"] = normalized
        return attrs


class QuestionnaireRetestTaskSerializer(serializers.ModelSerializer):
    questionnaire = QuestionnaireSerializer(read_only=True)
    student = UserMeSerializer(read_only=True)
    created_by = UserMeSerializer(read_only=True)

    class Meta:
        model = QuestionnaireRetestTask
        fields = [
            "id",
            "questionnaire",
            "student",
            "created_by",
            "reason",
            "due_date",
            "status",
            "completed_at",
            "created_at",
            "updated_at",
        ]


class QuestionnaireRetestTaskCreateSerializer(serializers.ModelSerializer):
    questionnaire_id = serializers.IntegerField(write_only=True)
    student_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = QuestionnaireRetestTask
        fields = ["id", "questionnaire_id", "student_id", "reason", "due_date"]

    def validate(self, attrs):
        questionnaire = Questionnaire.objects.select_related("target_college").filter(
            id=attrs["questionnaire_id"]
        ).first()
        if not questionnaire:
            raise serializers.ValidationError({"questionnaire_id": "无效问卷"})
        student = User.objects.filter(id=attrs["student_id"], role=User.Role.STUDENT).first()
        if not student:
            raise serializers.ValidationError({"student_id": "无效学生"})

        attrs["questionnaire"] = questionnaire
        attrs["student"] = student
        return attrs

    def create(self, validated_data):
        questionnaire = validated_data.pop("questionnaire")
        student = validated_data.pop("student")
        request = self.context.get("request")
        user = getattr(request, "user", None)

        existing = QuestionnaireRetestTask.objects.filter(
            questionnaire=questionnaire,
            student=student,
            status=QuestionnaireRetestTask.Status.PENDING,
        ).first()
        if existing:
            return existing

        return QuestionnaireRetestTask.objects.create(
            questionnaire=questionnaire,
            student=student,
            created_by=user if user and user.is_authenticated else None,
            **validated_data,
        )
