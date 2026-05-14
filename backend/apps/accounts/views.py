# accounts/views.py
# 该文件定义了 accounts 应用的视图，
# 包含了学院、专业、班级的视图集，以及用户注册、个人信息、咨询教师分配等相关视图的定义和实现。  
from django.contrib.auth import get_user_model
from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .assignment_utils import (
    assigned_counselors_for_student,
    counselor_student_ids,
    is_student_assigned_to_counselor,
)
from .models import ClassGroup, College, CounselorClassAssignment, CounselorStudent, Major
from .permissions import IsCounselor, IsSysAdmin
from .serializers import (
    AdminCreateUserSerializer,
    ClassGroupCreateSerializer,
    ClassGroupSerializer,
    CollegeSerializer,
    CounselorClassAssignmentSerializer,
    CounselorStudentSerializer,
    MajorCreateSerializer,
    MajorSerializer,
    RegisterStudentSerializer,
    UserMeSerializer,
)
User = get_user_model()

# 学院视图集（CollegeViewSet）提供了只读的接口，允许任何用户访问学院列表。
class CollegeViewSet(viewsets.ReadOnlyModelViewSet):
    # queryset 定义了视图集使用的查询集，这里是所有学院对象，并按照 ID 升序排序。
    queryset = College.objects.all().order_by("id")
    # serializer_class 定义了视图集使用的序列化器，这里是 CollegeSerializer，
    # 用于将学院对象转换为 JSON 格式。
    serializer_class = CollegeSerializer
    #定义了访问该视图集所需的权限， AllowAny，表示任何用户都可以访问学院列表接口。
    permission_classes = [AllowAny]

#registerStudentView 提供了一个接口，允许用户注册为学生。
class RegisterStudentView(generics.CreateAPIView):
    #它使用 RegisterStudentSerializer 进行数据验证和处理
    serializer_class = RegisterStudentSerializer
    permission_classes = [AllowAny]

# 个人信息视图（MeView）提供了一个接口，允许经过身份验证的用户获取自己的个人信息。
class MeView(generics.GenericAPIView):
    #permission_classes 定义了访问该视图所需的权限， IsAuthenticated，表示只有经过身份验证的用户才能访问该接口。
    permission_classes = [IsAuthenticated]
# 返回当前用户的个人信息。它使用 UserMeSerializer 将用户对象序列化为 JSON 格式，并返回给客户端。
    def get(self, request):
        return Response(UserMeSerializer(request.user).data)

# 允许系统管理员创建和查看用户列表。它使用 AdminCreateUserSerializer 进行数据验证和处理，并且只有具有系统管理员权限的用户才能访问该接口。
class AdminUserViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    # queryset 定义了视图集使用的查询集，这里是所有用户对象，
    # 并使用 select_related 优化查询以减少数据库访问次数，同时按照 ID 降序排序。
    queryset = User.objects.select_related(
        "college",
        "major",
        "class_group",
        "class_group__major",
    ).order_by("-id")
    # serializer_class 定义了视图集使用的序列化器，这里是 AdminCreateUserSerializer，
    # 用于将用户对象转换为 JSON 格式，并且在创建用户时进行数据验证和处理。
    serializer_class = AdminCreateUserSerializer
    permission_classes = [IsAuthenticated, IsSysAdmin]

# 提供了创建和查看专业列表的接口。
# 它使用 MajorSerializer 和 MajorCreateSerializer 进行数据验证和处理，
class MajorViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    # queryset 定义了视图集使用的查询集，这里是所有专业对象，
    # 并使用 select_related 优化查询以减少数据库访问次数，同时按照学院ID、专业名称和专业ID排序。
    queryset = Major.objects.select_related("college").order_by("college_id", "name", "id") 
    permission_classes = [IsAuthenticated]

# get_serializer_class 方法根据当前的操作（action）返回不同的序列化器类，
# 如果是创建操作（create），则返回 MajorCreateSerializer是用于创建专业的序列化器，否则返回 MajorSerializer 用于查看专业列表。
    def get_serializer_class(self):
        if self.action == "create":
            return MajorCreateSerializer
        return MajorSerializer
# get_permissions 方法根据当前的操作返回不同的权限类，
# 如果是创建操作（create），则返回 IsAuthenticated 和 IsSysAdmin，表示只有经过身份验证且具有系统管理员权限的用户才能创建专业，否则使用默认的权限类。
    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsSysAdmin()]
        return [AllowAny()]  # Allow unauthenticated users to list majors for registration
# get_queryset 方法根据请求的查询参数过滤专业列表，
# 如果请求中包含 college_id 参数，则过滤出属于该学院的专业；
# 如果请求中包含 major_id 参数，则过滤出属于该专业的专业。
    def get_queryset(self):
        qs = super().get_queryset()
        college_id = self.request.query_params.get("college_id")
        if college_id:
            qs = qs.filter(college_id=college_id)
        return qs

# 提供了创建和查看班级列表的接口。
# 它使用 ClassGroupSerializer 和 ClassGroupCreateSerializer 进行数据验证和处理，
# 并且在创建班级时，只有具有系统管理员权限的用户才能访问该接口。
class ClassGroupViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    # queryset 定义了视图集使用的查询集，这里是所有班级对象，
    # 并使用 select_related 优化查询以减少数据库访问次数，同时按照专业ID、班级名称和班级ID排序。
    queryset = ClassGroup.objects.select_related("major", "major__college").order_by(
        "major__college_id", "major_id", "name", "id"
    )
    permission_classes = [IsAuthenticated]
# get_serializer_class 方法根据当前的操作（action）返回不同的序列化器类，
# 如果是创建操作（create），则返回 ClassGroupCreateSerializer 是用于创建班级的序列化器，否则返回 ClassGroupSerializer 用于查看班级列表。
    def get_serializer_class(self):
        if self.action == "create":
            return ClassGroupCreateSerializer
        return ClassGroupSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsSysAdmin()]
        return [AllowAny()]  # Allow unauthenticated users to list classes for registration

    def get_queryset(self):
        qs = super().get_queryset()
        college_id = self.request.query_params.get("college_id")
        major_id = self.request.query_params.get("major_id")
        if major_id:
            qs = qs.filter(major_id=major_id)
        elif college_id:
            qs = qs.filter(major__college_id=college_id)
        return qs

# 提供了创建和查看咨询教师与学生分配关系的接口。它使用 CounselorStudentSerializer 进行数据验证和处理，
# 并且只有具有系统管理员权限的用户才能访问该接口。
class CounselorStudentViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = CounselorStudent.objects.select_related(
        "counselor",
        "counselor__college",
        "counselor__major",
        "counselor__class_group",
        "counselor__class_group__major",
        "student",
        "student__college",
        "student__major",
        "student__class_group",
        "student__class_group__major",
    ).order_by("-id")
    # serializer_class 定义了视图集使用的序列化器，这里是 CounselorStudentSerializer，
    # 用于将咨询教师与学生分配关系对象转换为 JSON 格式，并且在创建分配关系时进行数据验证和处理。
    serializer_class = CounselorStudentSerializer
    permission_classes = [IsAuthenticated, IsSysAdmin]

# 管理员给辅导员分配整个班级
# 班级下所有学生自动归这个辅导员管
# 可筛选查询
class CounselorClassAssignmentViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = CounselorClassAssignment.objects.select_related(
        "counselor",
        "counselor__college",
        "counselor__major",
        "counselor__class_group",
        "class_group",
        "class_group__major",
        "class_group__major__college",
    ).order_by("-id")
    serializer_class = CounselorClassAssignmentSerializer
    permission_classes = [IsAuthenticated, IsSysAdmin]
# get_queryset 方法根据请求的查询参数过滤咨询教师与班级分配关系列表，
# 如果请求中包含 counselor_id 参数，则过滤出属于该咨询教师的分配关系；
# 如果请求中包含 college_id 参数，则过滤出属于该学院的分配关系；
# 如果请求中包含 major_id 参数，则过滤出属于该专业的分配关系。  
    def get_queryset(self):
        qs = super().get_queryset()
        counselor_id = self.request.query_params.get("counselor_id")
        college_id = self.request.query_params.get("college_id")
        major_id = self.request.query_params.get("major_id")
        if counselor_id:
            qs = qs.filter(counselor_id=counselor_id)
        if major_id:
            qs = qs.filter(class_group__major_id=major_id)
        elif college_id:
            qs = qs.filter(class_group__major__college_id=college_id)
        return qs

# get_permissions 方法根据当前的操作返回不同的权限类，
# 如果是创建操作（create），则返回 IsAuthenticated 和 IsSysAdmin，
# 表示只有经过身份验证且具有系统管理员权限的用户才能创建分配关系，否则使用默认的权限类。
class CounselorStudentsView(generics.ListAPIView):
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated, IsCounselor]
# get_queryset 方法返回当前咨询教师负责的学生列表，
# 首先通过 counselor_student_ids 函数获取当前咨询教师负责的学生ID列表，
# 然后根据这些学生ID查询对应的学生对象，
# 并使用 select_related 优化查询以减少数据库访问次数，同时按照 ID 升序排序。  
    def get_queryset(self):
        user = self.request.user
        student_ids = counselor_student_ids(user)
        return (
            User.objects.filter(role=User.Role.STUDENT, id__in=student_ids)
            .select_related("college", "major", "class_group", "class_group__major")
            .order_by("id")
        )

# 学生个人信息视图（StudentProfileView）提供了一个接口，允许经过身份验证的用户获取特定学生的个人信息、
# 分配的咨询教师、最新的评估结果、风险预警、干预计划和重测任务等相关信息。  
class StudentProfileView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
# get 方法根据请求的学生ID（pk）查询对应的学生对象，并检查当前用户是否有权限访问该学生的信息。
    def get(self, request, pk: int):
        student = (
            User.objects.filter(id=pk, role=User.Role.STUDENT)
            .select_related("college", "major", "class_group", "class_group__major")
            .first()
        )
        if not student:
            return Response({"detail": "学生不存在"}, status=status.HTTP_404_NOT_FOUND)
# 根据用户角色和权限逻辑判断当前用户是否有权访问该学生的信息：
# 系统管理员可以访问所有学生的信息；
# 学生只能访问自己的信息；
# 咨询教师只能访问分配给自己的学生的信息；
# 二级学院管理员只能访问自己学院内学生的信息。
        user = request.user
        allowed = False
        if getattr(user, "is_sys_admin", False):
            allowed = True
        elif getattr(user, "is_student", False):
            allowed = user.id == student.id
        elif getattr(user, "is_counselor", False):
            allowed = is_student_assigned_to_counselor(counselor=user, student=student)
        elif getattr(user, "is_college_admin", False):
            allowed = bool(user.college_id and student.college_id == user.college_id)

        if not allowed:
            return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)

        assigned_counselors = assigned_counselors_for_student(student).select_related(
            "college", "major", "class_group", "class_group__major"
        )

        from apps.assessments.models import AssessmentResult, RiskAlert
        from apps.assessments.serializers import AssessmentResultSerializer, RiskAlertSerializer
        from apps.interventions.models import InterventionPlan
        from apps.interventions.serializers import InterventionPlanSerializer
# 获取学生的最新评估结果、最近的风险预警和干预计划，以及最近的评估结果列表（最多8条），并使用相应的序列化器将这些对象转换为 JSON 格式返回给客户端。
        latest_assessment = (
            AssessmentResult.objects.select_related(
                "response",
                "response__student",
                "response__questionnaire",
                "response__questionnaire__template",
                "response__questionnaire__target_college",
            )
            .filter(response__student=student)
            .order_by("-id")
            .first()
        )# 获取学生的最新评估结果，按照 ID 降序排序，并返回第一条记录（即最新的评估结果）。
        latest_alerts = (
            RiskAlert.objects.select_related("student", "acknowledged_by")
            .filter(student=student)
            .order_by("-id")[:10]
        )# 获取学生的最近风险预警，按照 ID 降序排序，并返回前10条记录。
        plans = (
            InterventionPlan.objects.select_related("student", "counselor", "assessment")
            .filter(student=student)
            .order_by("-id")[:10]
        )# 获取学生的最近干预计划，按照 ID 降序排序，并返回前10条记录。
        recent_assessments_qs = (
            AssessmentResult.objects.select_related(
                "response",
                "response__student",
                "response__questionnaire",
                "response__questionnaire__template",
                "response__questionnaire__target_college",
            )
            .filter(response__student=student)
            .order_by("-id")[:8]
        )# 获取学生的最近评估结果列表，按照 ID 降序排序，并返回前8条记录。由于后续需要将这些评估结果按照时间顺序（从旧到新）返回给客户端，因此先将查询集转换为列表，然后使用 reversed 函数反转列表的顺序。
        #将查询集转换为列表，以便后续进行排序和处理。
        recent_assessments = list(recent_assessments_qs)
        # 将最近评估结果列表反转，使其按照时间顺序（从旧到新）排序，方便客户端展示。
        recent_assessments_sorted = list(reversed(recent_assessments))

        from apps.surveys.models import QuestionnaireRetestTask
        from apps.surveys.serializers import QuestionnaireRetestTaskSerializer

        retest_tasks = (
            QuestionnaireRetestTask.objects.select_related(
                "student",
                "created_by",
                "questionnaire",
                "questionnaire__template",
                "questionnaire__target_college",
                "questionnaire__created_by",
            )
            .filter(student=student)
            .order_by("-id")[:10]
        )# 获取学生的最近重测任务，按照 ID 降序排序，并返回前10条记录。

        return Response(
            {
                "student": UserMeSerializer(student).data,
                "assigned_counselors": UserMeSerializer(assigned_counselors, many=True).data,
                "latest_assessment": AssessmentResultSerializer(latest_assessment).data
                if latest_assessment
                else None,
                "recent_assessments": AssessmentResultSerializer(recent_assessments_sorted, many=True).data,
                "latest_alerts": RiskAlertSerializer(latest_alerts, many=True).data,
                "intervention_plans": InterventionPlanSerializer(plans, many=True).data,
                "retest_tasks": QuestionnaireRetestTaskSerializer(retest_tasks, many=True).data,
            }
        )# 返回一个包含学生个人信息、分配的咨询教师、最新评估结果、最近评估结果列表、
    #最近风险预警、干预计划和重测任务等相关信息的 JSON 响应。
