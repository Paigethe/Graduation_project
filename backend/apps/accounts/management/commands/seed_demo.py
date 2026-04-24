from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import College, CounselorStudent, User
from apps.assessments.models import AssessmentResult
from apps.assessments.services import create_assessment_for_response
from apps.chat.models import Conversation, Message
from apps.chat.utils import encrypt_text
from apps.interventions.models import InterventionPlan
from apps.knowledge.models import KnowledgeArticle, KnowledgeCategory
from apps.surveys.models import Questionnaire, QuestionnaireResponse, QuestionnaireTemplate

DEFAULT_PASSWORD = "123456"
COLLEGE_SPECS = [
    ("计算机学院", "cs"),
    ("外国语学院", "fl"),
    ("机械工程学院", "me"),
    ("经济管理学院", "biz"),
]

SCL90_DIM_TEXTS = {
    "somatization": [
        "最近一周我常有不明原因的头痛或身体酸痛。",
        "最近一周我会反复感到胃部不适或食欲异常。",
        "最近一周我容易出现心慌、胸闷等身体反应。",
        "最近一周我经常感觉精力不足、身体沉重。",
        "最近一周我会担心自己身体出现严重问题。",
        "最近一周我会因为身体小毛病而明显紧张。",
        "最近一周我常感到四肢乏力或发软。",
        "最近一周我会被睡眠相关的身体不适困扰。",
        "最近一周我的身体状态影响了学习/生活节奏。",
    ],
    "compulsive": [
        "最近一周我会反复检查同一件事是否完成。",
        "最近一周我很难停止脑中重复出现的念头。",
        "最近一周我做事会过度追求完美而拖延。",
        "最近一周我常因担心出错而重复确认细节。",
        "最近一周我会反复回想已发生的小失误。",
        "最近一周我在学习时常被“必须这样做”困住。",
        "最近一周我会因反复犹豫而难以下决定。",
        "最近一周我会按固定顺序做事，否则不安。",
        "最近一周我会因反复整理/重做而耗费很多时间。",
    ],
    "interpersonal": [
        "最近一周我在人际互动中容易紧张或不自在。",
        "最近一周我会过度在意别人对我的看法。",
        "最近一周我与同学沟通时担心被否定。",
        "最近一周我会因为社交场合而感到明显压力。",
        "最近一周我在人多场景里容易感到拘谨。",
        "最近一周我会避免主动表达自己的真实想法。",
        "最近一周我在人际冲突后会持续自责。",
        "最近一周我感觉自己不太容易被他人理解。",
        "最近一周我与他人相处时常感到被比较或被评判。",
    ],
    "depression": [
        "最近一周我对原本感兴趣的事情提不起劲。",
        "最近一周我经常感到情绪低落或无助。",
        "最近一周我会觉得做什么都没有意义。",
        "最近一周我比平时更容易疲惫、动力不足。",
        "最近一周我会对自己产生明显否定感。",
        "最近一周我常觉得未来看起来缺乏希望。",
        "最近一周我难以从日常小事中感到愉快。",
        "最近一周我会持续处在压抑的心情中。",
        "最近一周我会因为情绪问题影响学习效率。",
    ],
    "anxiety": [
        "最近一周我经常感到紧张、担忧难以放松。",
        "最近一周我会因为小事反复焦虑。",
        "最近一周我容易出现坐立不安的状态。",
        "最近一周我会对未发生的事情提前担心。",
        "最近一周我在压力情境下容易慌乱。",
        "最近一周我难以让自己平静下来。",
        "最近一周我会因学习任务产生持续焦虑感。",
        "最近一周我在夜间更容易出现担心和烦躁。",
        "最近一周焦虑情绪已影响我的专注与休息。",
    ],
    "hostility": [
        "最近一周我比平时更容易烦躁或发脾气。",
        "最近一周我会对他人的言行产生明显不满。",
        "最近一周我常有“容易被激怒”的体验。",
        "最近一周我在人际摩擦中更难控制情绪。",
        "最近一周我会因小冲突持续生气。",
        "最近一周我对周围环境更容易产生敌意。",
        "最近一周我会在沟通中不自觉提高语气。",
        "最近一周我会因压力大而迁怒他人。",
        "最近一周我经常感觉心里憋闷、想发泄。",
    ],
    "phobic": [
        "最近一周我在特定场景会出现明显害怕感。",
        "最近一周我会因为陌生环境而回避出行。",
        "最近一周我在公开场合容易紧张到想逃离。",
        "最近一周我会担心某些情境发生失控。",
        "最近一周我会因恐惧而主动减少社交活动。",
        "最近一周我在人群密集处会明显不安。",
        "最近一周我会回避自己觉得“危险”的地点。",
        "最近一周我在考试/汇报前会出现强烈害怕。",
        "最近一周恐惧情绪已影响我正常安排。",
    ],
    "paranoid": [
        "最近一周我会怀疑他人对我有负面意图。",
        "最近一周我容易把中性言行理解成针对我。",
        "最近一周我会担心别人背后议论自己。",
        "最近一周我在人际中更容易保持防备状态。",
        "最近一周我会对他人评价过度敏感。",
        "最近一周我常担心自己被误解或被针对。",
        "最近一周我对周围人的信任感有所下降。",
        "最近一周我会反复揣测他人的真实想法。",
        "最近一周我在团队协作中更难放松。",
    ],
    "psychoticism": [
        "最近一周我会感到与周围人有明显疏离感。",
        "最近一周我偶尔会有不真实或恍惚的感觉。",
        "最近一周我会觉得自己的想法难被理解。",
        "最近一周我感到思路有时变得混乱。",
        "最近一周我会出现难以描述的怪异不适感。",
        "最近一周我会因心理压力感到“脱节”。",
        "最近一周我在情绪波动时会有失控担忧。",
        "最近一周我会觉得自己和环境不太协调。",
        "最近一周我经常感到内心紧绷又难以言说。",
    ],
    "additional": [
        "最近一周我的睡眠质量明显下降。",
        "最近一周我在起床后仍感到疲惫。",
        "最近一周我的食欲较平时变化明显。",
        "最近一周我会因情绪问题影响日常效率。",
        "最近一周我更容易因小问题反复担忧。",
        "最近一周我会对未来安排感到迷茫。",
        "最近一周我难以维持稳定的学习节奏。",
        "最近一周我会觉得身心都处在高压状态。",
        "最近一周我需要更多支持才能维持状态。",
    ],
}

SAS_TEXTS = [
    "我会无明显原因地感到紧张不安。",
    "我容易因为小事而心里发慌。",
    "我在安静时也会感到难以放松。",
    "我常担心不好的事情会发生在自己身上。",
    "我在学习任务前会过度紧张。",
    "我会出现坐立不安、难以静下来的情况。",
    "我常觉得心跳加快或有紧迫感。",
    "我会因未来不确定而持续担忧。",
    "我容易因为他人评价而焦虑。",
    "我在睡前常因担心而难以入睡。",
    "我经常感觉神经绷得很紧。",
    "我在压力下会明显烦躁。",
    "我会反复思考同一件担心的事。",
    "我在公共场合容易紧张。",
    "我会因学习节奏而感到持续焦虑。",
    "我常担心自己表现不够好。",
    "我在突发变化面前容易慌乱。",
    "我近期更容易疲惫且难以恢复。",
    "我会因焦虑影响专注力。",
    "我总体上感觉焦虑程度较高。",
]

SDS_TEXTS = [
    "我最近情绪低落的时间变多了。",
    "我对曾经喜欢的事情兴趣下降。",
    "我会觉得做事提不起精神。",
    "我常感到疲惫、动力不足。",
    "我会觉得自己价值感降低。",
    "我对未来有时缺乏希望。",
    "我在学习中容易感到无力。",
    "我比平时更想独处。",
    "我在社交中变得被动。",
    "我会出现持续性的消极想法。",
    "我最近做事效率明显下降。",
    "我会因情绪问题影响作息。",
    "我常觉得开心变得困难。",
    "我会否定自己的能力与表现。",
    "我有时觉得生活缺少意义感。",
    "我面对压力时更容易沮丧。",
    "我最近容易陷入自责情绪。",
    "我会因小挫折而情绪下滑很久。",
    "我总体上感到情绪较压抑。",
    "我感觉需要外部支持来调整状态。",
]


def _scl90_questions() -> list[dict]:
    dims = [
        "somatization",
        "compulsive",
        "interpersonal",
        "depression",
        "anxiety",
        "hostility",
        "phobic",
        "paranoid",
        "psychoticism",
        "additional",
    ]
    questions: list[dict] = []
    for idx in range(1, 91):
        dim = dims[(idx - 1) // 9]
        text = SCL90_DIM_TEXTS[dim][(idx - 1) % 9]
        questions.append(
            {
                "id": idx,
                "text": f"SCL90模拟题{idx:02d}：{text}",
                "dimension": dim,
                "weight": 1,
                "min": 1,
                "max": 5,
            }
        )
    return questions


def _sas_questions() -> list[dict]:
    reverse_ids = {5, 9, 13, 17, 19}
    questions: list[dict] = []
    for idx in range(1, 21):
        q = {
            "id": idx,
            "text": f"SAS模拟题{idx:02d}：{SAS_TEXTS[idx - 1]}",
            "dimension": "anxiety",
            "weight": 1,
            "min": 1,
            "max": 4,
        }
        if idx in reverse_ids:
            q["reverse"] = True
        questions.append(q)
    return questions


def _sds_questions() -> list[dict]:
    reverse_ids = {2, 5, 6, 11, 12, 14, 16, 17, 18, 20}
    questions: list[dict] = []
    for idx in range(1, 21):
        q = {
            "id": idx,
            "text": f"SDS模拟题{idx:02d}：{SDS_TEXTS[idx - 1]}",
            "dimension": "depression",
            "weight": 1,
            "min": 1,
            "max": 4,
        }
        if idx in reverse_ids:
            q["reverse"] = True
        questions.append(q)
    return questions


class Command(BaseCommand):
    help = "Seed demo data for BS/001 (idempotent, richer dataset)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--students-per-college",
            type=int,
            default=20,
            help="Extra generated students per college (default: 20)",
        )
        parser.add_argument(
            "--counselors-per-college",
            type=int,
            default=2,
            help="Generated counselors per college (default: 2)",
        )
        parser.add_argument(
            "--responses-per-questionnaire",
            type=int,
            default=12,
            help="Max responses generated for each questionnaire (default: 12)",
        )
        parser.add_argument(
            "--history-days",
            type=int,
            default=90,
            help="Distribute simulated records across N recent days (default: 90)",
        )

    def _ensure_user(
        self,
        username: str,
        *,
        role: str,
        real_name: str,
        college: College | None = None,
        student_no: str = "",
        is_staff: bool = False,
        is_superuser: bool = False,
    ) -> User:
        defaults = {
            "role": role,
            "real_name": real_name,
            "college": college,
            "student_no": student_no,
            "is_staff": is_staff,
            "is_superuser": is_superuser,
        }
        user, created = User.objects.get_or_create(username=username, defaults=defaults)

        updated_fields: list[str] = []
        for field, value in defaults.items():
            current = getattr(user, field)
            if current != value:
                setattr(user, field, value)
                updated_fields.append(field)
        if updated_fields:
            user.save(update_fields=updated_fields)

        if created:
            user.set_password(DEFAULT_PASSWORD)
            user.save(update_fields=["password"])

        return user

    def _upsert_template(
        self,
        *,
        name: str,
        scale_type: str,
        description: str,
        questions: list[dict],
    ) -> QuestionnaireTemplate:
        template, created = QuestionnaireTemplate.objects.get_or_create(
            name=name,
            defaults={
                "scale_type": scale_type,
                "description": description,
                "questions": questions,
            },
        )
        if not created:
            changed_fields = []
            if template.scale_type != scale_type:
                template.scale_type = scale_type
                changed_fields.append("scale_type")
            if template.description != description:
                template.description = description
                changed_fields.append("description")
            if template.questions != questions:
                template.questions = questions
                changed_fields.append("questions")
            if changed_fields:
                template.save(update_fields=changed_fields)
        return template

    def _upsert_questionnaire(
        self,
        *,
        title: str,
        template: QuestionnaireTemplate,
        description: str,
        created_by: User,
        target_college: College | None,
        is_active: bool = True,
    ) -> Questionnaire:
        questionnaire = Questionnaire.objects.filter(title=title, target_college=target_college).first()
        if not questionnaire:
            questionnaire = Questionnaire.objects.create(
                template=template,
                title=title,
                description=description,
                is_active=is_active,
                target_college=target_college,
                created_by=created_by,
            )
            return questionnaire

        changed_fields = []
        if questionnaire.template_id != template.id:
            questionnaire.template = template
            changed_fields.append("template")
        if questionnaire.description != description:
            questionnaire.description = description
            changed_fields.append("description")
        if questionnaire.created_by_id != created_by.id:
            questionnaire.created_by = created_by
            changed_fields.append("created_by")
        if questionnaire.is_active != is_active:
            questionnaire.is_active = is_active
            changed_fields.append("is_active")
        if changed_fields:
            questionnaire.save(update_fields=changed_fields)
        return questionnaire

    def _pick_bucket(self, idx: int) -> str:
        slot = idx % 10
        if slot <= 5:
            return "low"
        if slot <= 8:
            return "medium"
        return "high"

    def _answer_value(self, minimum: int, maximum: int, bucket: str, salt: int) -> int:
        span = max(0, maximum - minimum)
        if span == 0:
            return minimum

        if bucket == "low":
            low = minimum
            high = min(maximum, minimum + max(1, span // 2))
        elif bucket == "medium":
            low = min(maximum, minimum + max(1, span // 3))
            high = max(low, max(minimum, maximum - max(1, span // 3)))
        else:
            low = max(minimum, maximum - max(1, span // 2))
            high = maximum

        if high < low:
            low, high = high, low
        return low + (salt % (high - low + 1))

    def _build_answers(self, *, questions: list[dict], student_id: int, idx: int, bucket: str) -> dict[str, int]:
        answers: dict[str, int] = {}
        for q in questions:
            qid = int(q.get("id") or 0)
            if not qid:
                continue
            minimum = int(q.get("min") or 1)
            maximum = int(q.get("max") or 5)
            salt = student_id * 131 + qid * 17 + idx * 29
            answers[str(qid)] = self._answer_value(minimum, maximum, bucket, salt)
        return answers

    def _seed_knowledge(self, *, colleges: dict[str, College], owner: User) -> None:
        categories = [
            "情绪管理",
            "学习压力",
            "人际关系",
            "睡眠健康",
            "危机识别",
        ]
        cat_map = {
            name: KnowledgeCategory.objects.get_or_create(name=name)[0] for name in categories
        }

        global_articles = [
            ("考试周减压四步法（示例）", "学习压力", "把任务拆到30分钟粒度，按番茄钟完成。"),
            ("宿舍关系冲突降温指南（示例）", "人际关系", "先描述事实，再表达感受，最后提出可执行请求。"),
            ("改善睡眠节律的三个习惯（示例）", "睡眠健康", "固定起床时间、减少晚间强光、睡前放松。"),
            ("情绪急救卡（示例）", "情绪管理", "识别情绪-呼吸放松-找人求助，按顺序执行。"),
        ]

        for title, cat_name, content in global_articles:
            KnowledgeArticle.objects.get_or_create(
                title=title,
                defaults={
                    "category": cat_map[cat_name],
                    "summary": content,
                    "content": content,
                    "target_college": None,
                    "created_by": owner,
                    "is_published": True,
                },
            )

        for college in colleges.values():
            title = f"{college.name}心理支持资源导航（示例）"
            body = (
                f"面向{college.name}学生的模拟资源页：\n"
                "1) 学业压力：每周复盘一次；\n"
                "2) 睡眠作息：固定起床；\n"
                "3) 人际支持：和同伴建立支持清单。"
            )
            KnowledgeArticle.objects.get_or_create(
                title=title,
                defaults={
                    "category": cat_map["情绪管理"],
                    "summary": f"{college.name}学院定向心理支持资源（示例）",
                    "content": body,
                    "target_college": college,
                    "created_by": owner,
                    "is_published": True,
                },
            )

    def _seed_chat_samples(
        self,
        *,
        students_by_college: dict[str, list[User]],
        counselors_by_college: dict[str, list[User]],
    ) -> None:
        now = timezone.now()
        for key, students in students_by_college.items():
            counselors = counselors_by_college.get(key) or []
            if not counselors:
                continue

            for idx, student in enumerate(students[:6]):
                counselor = counselors[idx % len(counselors)]
                conv, _ = Conversation.objects.get_or_create(
                    kind=Conversation.Kind.HUMAN,
                    student=student,
                    counselor=counselor,
                )
                if conv.messages.count() == 0:
                    s_msg = Message.objects.create(
                        conversation=conv,
                        sender=student,
                        sender_kind="user",
                        content_ciphertext=encrypt_text("老师您好，我最近压力有点大。"),
                    )
                    c_msg = Message.objects.create(
                        conversation=conv,
                        sender=counselor,
                        sender_kind="user",
                        content_ciphertext=encrypt_text("收到，我们可以先从作息和任务分解开始。"),
                    )
                    Message.objects.filter(id=s_msg.id).update(read_at=now)
                    Message.objects.filter(id=c_msg.id).update(read_at=now)
                    conv.save(update_fields=["updated_at"])

            for student in students[:4]:
                conv, _ = Conversation.objects.get_or_create(
                    kind=Conversation.Kind.AI,
                    student=student,
                    counselor=None,
                )
                if conv.messages.count() == 0:
                    Message.objects.create(
                        conversation=conv,
                        sender=student,
                        sender_kind="user",
                        content_ciphertext=encrypt_text("最近睡眠不好，还总是焦虑。"),
                    )
                    Message.objects.create(
                        conversation=conv,
                        sender=None,
                        sender_kind="ai",
                        content_ciphertext=encrypt_text("先做一分钟呼吸放松，我也会给你推送相关建议。"),
                    )
                    conv.save(update_fields=["updated_at"])

    def handle(self, *args, **options):
        students_per_college = max(0, int(options["students_per_college"]))
        counselors_per_college = max(1, int(options["counselors_per_college"]))
        responses_per_q = max(0, int(options["responses_per_questionnaire"]))
        history_days = max(1, int(options["history_days"]))

        colleges: dict[str, College] = {}
        for name, key in COLLEGE_SPECS:
            college, _ = College.objects.get_or_create(name=name)
            colleges[key] = college

        admin = self._ensure_user(
            "admin",
            role=User.Role.SYS_ADMIN,
            real_name="系统管理员",
            is_staff=True,
            is_superuser=True,
        )

        college_admin = self._ensure_user(
            "college_admin",
            role=User.Role.COLLEGE_ADMIN,
            real_name="二级学院管理员",
            college=colleges["cs"],
        )

        counselor1 = self._ensure_user(
            "counselor1",
            role=User.Role.COUNSELOR,
            real_name="咨询教师1",
            college=colleges["cs"],
        )
        student1 = self._ensure_user(
            "student1",
            role=User.Role.STUDENT,
            real_name="学生甲",
            college=colleges["cs"],
            student_no="S20260001",
        )
        student2 = self._ensure_user(
            "student2",
            role=User.Role.STUDENT,
            real_name="学生乙",
            college=colleges["cs"],
            student_no="S20260002",
        )

        counselors_by_college: dict[str, list[User]] = {key: [] for _name, key in COLLEGE_SPECS}
        students_by_college: dict[str, list[User]] = {key: [] for _name, key in COLLEGE_SPECS}
        admins_by_college: dict[str, User] = {}

        counselors_by_college["cs"].append(counselor1)
        students_by_college["cs"].extend([student1, student2])
        admins_by_college["cs"] = college_admin

        for idx, (_name, key) in enumerate(COLLEGE_SPECS, start=1):
            college = colleges[key]
            admin_username = f"{key}_admin"
            college_owner = self._ensure_user(
                admin_username,
                role=User.Role.COLLEGE_ADMIN,
                real_name=f"{college.name}管理员",
                college=college,
            )
            admins_by_college[key] = college_owner if key != "cs" else college_admin

            for c_idx in range(1, counselors_per_college + 1):
                username = f"{key}_counselor_{c_idx:02d}"
                counselor = self._ensure_user(
                    username,
                    role=User.Role.COUNSELOR,
                    real_name=f"{college.name}咨询教师{c_idx}",
                    college=college,
                )
                if counselor.id not in {x.id for x in counselors_by_college[key]}:
                    counselors_by_college[key].append(counselor)

            for s_idx in range(1, students_per_college + 1):
                username = f"{key}_student_{s_idx:03d}"
                student = self._ensure_user(
                    username,
                    role=User.Role.STUDENT,
                    real_name=f"{college.name}学生{s_idx:03d}",
                    college=college,
                    student_no=f"S2026{idx:02d}{s_idx:03d}",
                )
                students_by_college[key].append(student)

        for key in students_by_college:
            counselors = sorted(counselors_by_college[key], key=lambda x: x.username)
            students = sorted(students_by_college[key], key=lambda x: x.username)
            if not counselors:
                continue
            for idx, student in enumerate(students):
                counselor = counselors[idx % len(counselors)]
                CounselorStudent.objects.get_or_create(counselor=counselor, student=student)

        self._seed_knowledge(colleges=colleges, owner=college_admin)

        sample_tpl = self._upsert_template(
            name="SCL-90 示例（10题）",
            scale_type=QuestionnaireTemplate.ScaleType.SCL90_SAMPLE,
            description="用于演示系统闭环的示例问卷（非正式量表题干）。",
            questions=[
                {"id": 1, "text": "示例题：最近我感到紧张不安。", "dimension": "anxiety", "weight": 1, "min": 1, "max": 5},
                {"id": 2, "text": "示例题：我很难放松下来。", "dimension": "anxiety", "weight": 1, "min": 1, "max": 5},
                {"id": 3, "text": "示例题：我对以前感兴趣的事提不起劲。", "dimension": "depression", "weight": 1, "min": 1, "max": 5},
                {"id": 4, "text": "示例题：我觉得做什么都很累。", "dimension": "depression", "weight": 1, "min": 1, "max": 5},
                {"id": 5, "text": "示例题：我最近睡眠质量不佳。", "dimension": "sleep", "weight": 1, "min": 1, "max": 5},
                {"id": 6, "text": "示例题：我经常难以入睡或易醒。", "dimension": "sleep", "weight": 1, "min": 1, "max": 5},
                {"id": 7, "text": "示例题：我在人际相处中感到压力。", "dimension": "social", "weight": 1, "min": 1, "max": 5},
                {"id": 8, "text": "示例题：我担心别人对我的看法。", "dimension": "social", "weight": 1, "min": 1, "max": 5},
                {"id": 9, "text": "示例题：我最近食欲变化明显。", "dimension": "somatic", "weight": 1, "min": 1, "max": 5},
                {"id": 10, "text": "示例题：我常感到身体不适但查不出原因。", "dimension": "somatic", "weight": 1, "min": 1, "max": 5},
            ],
        )

        scl90_tpl = self._upsert_template(
            name="SCL-90 结构化模拟量表（90题）",
            scale_type=QuestionnaireTemplate.ScaleType.SCL90_SAMPLE,
            description="结构化模拟题库（非版权原题），用于流程联调与模型接口验证。",
            questions=_scl90_questions(),
        )
        sas_tpl = self._upsert_template(
            name="SAS 结构化模拟量表（20题）",
            scale_type=QuestionnaireTemplate.ScaleType.SAS_SAMPLE,
            description="结构化模拟题库（非版权原题），包含反向计分标记。",
            questions=_sas_questions(),
        )
        sds_tpl = self._upsert_template(
            name="SDS 结构化模拟量表（20题）",
            scale_type=QuestionnaireTemplate.ScaleType.SDS_SAMPLE,
            description="结构化模拟题库（非版权原题），包含反向计分标记。",
            questions=_sds_questions(),
        )

        questionnaires: list[Questionnaire] = []
        questionnaires.append(
            self._upsert_questionnaire(
                title="心理健康自评（示例）",
                template=sample_tpl,
                description="面向计算机学院学生的示例问卷。",
                is_active=True,
                target_college=colleges["cs"],
                created_by=college_admin,
            )
        )

        for _name, key in COLLEGE_SPECS:
            college = colleges[key]
            owner = admins_by_college[key]
            questionnaires.extend(
                [
                    self._upsert_questionnaire(
                        title=f"{college.name}心理健康筛查（SCL90模拟）",
                        template=scl90_tpl,
                        description="学院心理普查用结构化模拟问卷。",
                        target_college=college,
                        created_by=owner,
                    ),
                    self._upsert_questionnaire(
                        title=f"{college.name}焦虑状态筛查（SAS模拟）",
                        template=sas_tpl,
                        description="学院焦虑状态筛查模拟问卷。",
                        target_college=college,
                        created_by=owner,
                    ),
                    self._upsert_questionnaire(
                        title=f"{college.name}抑郁状态筛查（SDS模拟）",
                        template=sds_tpl,
                        description="学院抑郁状态筛查模拟问卷。",
                        target_college=college,
                        created_by=owner,
                    ),
                ]
            )

        questionnaires.append(
            self._upsert_questionnaire(
                title="全校心理普查（SCL90模拟）",
                template=scl90_tpl,
                description="全校范围模拟普查问卷（目标学院为空表示全校）。",
                target_college=None,
                created_by=admin,
                is_active=True,
            )
        )

        now = timezone.now()
        for q_idx, questionnaire in enumerate(questionnaires):
            if questionnaire.target_college_id:
                key = next(k for _name, k in COLLEGE_SPECS if colleges[k].id == questionnaire.target_college_id)
                candidate_students = sorted(students_by_college[key], key=lambda x: x.username)
            else:
                candidate_students = sorted(
                    [s for group in students_by_college.values() for s in group],
                    key=lambda x: x.username,
                )

            sample_size = min(responses_per_q, len(candidate_students))
            for s_idx, student in enumerate(candidate_students[:sample_size]):
                bucket = self._pick_bucket(s_idx + q_idx)
                answers = self._build_answers(
                    questions=questionnaire.template.questions or [],
                    student_id=student.id,
                    idx=s_idx + q_idx,
                    bucket=bucket,
                )
                response, created = QuestionnaireResponse.objects.get_or_create(
                    questionnaire=questionnaire,
                    student=student,
                    defaults={"answers": answers},
                )
                if not created and response.answers != answers:
                    response.answers = answers
                    response.save(update_fields=["answers"])

                submitted_at = now - timedelta(days=((s_idx + q_idx) % history_days), hours=(q_idx % 6))
                QuestionnaireResponse.objects.filter(id=response.id).update(submitted_at=submitted_at)
                response.refresh_from_db(fields=["submitted_at"])

                assessment = getattr(response, "assessment", None)
                if assessment is None:
                    assessment = create_assessment_for_response(response)

                assessment_created = submitted_at + timedelta(minutes=5)
                AssessmentResult.objects.filter(id=assessment.id).update(created_at=assessment_created)

                if assessment.risk_level in {
                    AssessmentResult.RiskLevel.MEDIUM,
                    AssessmentResult.RiskLevel.HIGH,
                }:
                    link = CounselorStudent.objects.filter(student=student).select_related("counselor").first()
                    counselor = link.counselor if link else None
                    if counselor:
                        InterventionPlan.objects.get_or_create(
                            student=student,
                            assessment=assessment,
                            defaults={
                                "counselor": counselor,
                                "title": "风险学生跟进计划（模拟）",
                                "content": "1) 本周完成一次面谈；2) 每日情绪打卡；3) 睡眠与作息调整。",
                                "status": InterventionPlan.Status.IN_PROGRESS,
                            },
                        )

        self._seed_chat_samples(
            students_by_college=students_by_college,
            counselors_by_college=counselors_by_college,
        )

        stats = {
            "colleges": College.objects.count(),
            "users": User.objects.count(),
            "templates": QuestionnaireTemplate.objects.count(),
            "questionnaires": Questionnaire.objects.count(),
            "responses": QuestionnaireResponse.objects.count(),
            "assessments": AssessmentResult.objects.count(),
            "knowledge_articles": KnowledgeArticle.objects.count(),
            "intervention_plans": InterventionPlan.objects.count(),
            "conversations": Conversation.objects.count(),
            "messages": Message.objects.count(),
        }

        summary = ", ".join(f"{k}={v}" for k, v in stats.items())
        self.stdout.write(self.style.SUCCESS(f"seed_demo done: {summary}"))
