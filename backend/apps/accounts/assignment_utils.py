#辅导员（Counselor） 与学生（Student） 之间的关联关系管理
from __future__ import annotations

from django.contrib.auth import get_user_model
# 系统支持两种分配方式：
# 直接分配 - 咨询师直接负责特定学生（CounselorStudent 模型）
# 班级分配 - 咨询师负责整个班级的所有学生（CounselorClassAssignment 模型）
from .models import CounselorClassAssignment, CounselorStudent

User = get_user_model()

#获取咨询师负责的所有学生ID列表
def counselor_student_ids(counselor: User) -> list[int]:
    ## 1. 获取直接关联的学生ID
    direct_ids = list(
        CounselorStudent.objects.filter(counselor=counselor).values_list("student_id", flat=True)
    )
    ## 2. 获取班级关联的学生ID 
    # 先查辅导员绑定的班级，再查这些班级下的所有学生ID
    class_ids = list(
        # 只查询学生角色，并且班级ID在辅导员负责的班级列表中的学生ID
        User.objects.filter(
            # 只查询学生角色
            role=User.Role.STUDENT,
            # 班级ID在辅导员负责的班级列表中
            class_group_id__in=CounselorClassAssignment.objects.filter(counselor=counselor).values_list(
                "class_group_id", flat=True
            ),
        ).values_list("id", flat=True)
    )
    # 3. 合并去重后返回所有学生ID列表
    return sorted(set(int(x) for x in [*direct_ids, *class_ids]))

# 判断某个学生是否被某个咨询师负责（直接或通过班级分配）/检查学生是否分配给指定咨询师
def is_student_assigned_to_counselor(*, counselor: User, student: User) -> bool:
    # 1. 先检查直接分配关系，如果存在直接分配关系，立即返回 True
    if CounselorStudent.objects.filter(counselor=counselor, student=student).exists():
        return True
    # 如果学生没有班级信息，直接返回 False（因为无法通过班级分配）
    if not getattr(student, "class_group_id", None):
        return False
     # 3. 检查学生所在班级是否绑定该辅导员
    return CounselorClassAssignment.objects.filter(
        counselor=counselor, class_group_id=student.class_group_id
    ).exists()

# 获取负责某个学生的所有咨询师ID列表（直接分配和班级分配的咨询师ID）
def assigned_counselor_ids_for_student(student: User) -> list[int]:
    # 直接分配的咨询师ID列表
    direct_ids = list(
        CounselorStudent.objects.filter(student=student).values_list("counselor_id", flat=True)
    )
    # 班级分配的咨询师ID列表
    class_ids = []
    # 如果学生有班级信息，查询负责该班级的咨询师ID列表 （如果没有班级信息，则无法通过班级分配，所以直接跳过这步） 
    if getattr(student, "class_group_id", None):
        class_ids = list(
            CounselorClassAssignment.objects.filter(class_group_id=student.class_group_id).values_list(
                "counselor_id", flat=True
            )
        )
        ## 3. 合并、去重、排序后返回
    return sorted(set(int(x) for x in [*direct_ids, *class_ids]))

# 获取负责某个学生的所有咨询师对象列表（直接分配和班级分配的咨询师对象）
def assigned_counselors_for_student(student: User):
    # 获取负责该学生的所有咨询师ID列表
    ids = assigned_counselor_ids_for_student(student)
    # 如果没有任何咨询师负责该学生，直接返回一个空的查询集（避免后续查询出错）
    if not ids:
        return User.objects.none()
    # 根据咨询师ID列表查询对应的咨询师对象，并按照ID排序返回
    return User.objects.filter(id__in=ids, role=User.Role.COUNSELOR).order_by("id")

# 获取负责某个学生的第一个咨询师对象
#（按照ID排序，优先返回直接分配的咨询师，如果没有直接分配的咨询师，则返回班级分配的咨询师）
def first_assigned_counselor_for_student(student: User):
    # 1. 优先查询直接分配的咨询师，如果存在直接分配的咨询师，立即返回第一个（ID最小的）咨询师对象
    direct = (
        User.objects.filter(
            id__in=CounselorStudent.objects.filter(student=student).values_list("counselor_id", flat=True),
            # 只查询咨询师角色
            role=User.Role.COUNSELOR,
        )
        .order_by("id")
        .first()
    )
    if direct:
        return direct
     # 2. 学生无班级则返回None（因为无法通过班级分配）
    if not getattr(student, "class_group_id", None):
        return None
    # 3. 如果没有直接分配的咨询师，查询班级分配的咨询师，并返回第一个（ID最小的）咨询师对象
    return (
        User.objects.filter(
            id__in=CounselorClassAssignment.objects.filter(
                class_group_id=student.class_group_id
            ).values_list("counselor_id", flat=True),
            role=User.Role.COUNSELOR,
        )
        .order_by("id")
        .first()
    )
