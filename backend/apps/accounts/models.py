#本文件是accounts应用的模型定义文件，
# 包含了用户、学院、专业、班级等相关模型的定义，以及咨询师与学生的分配关系模型。
from django.contrib.auth.models import AbstractUser
from django.db import models

#  学院模型，表示学校的学院，每个学院有一个唯一的名称。
class College(models.Model):
    # 学院名称，字符串类型，最大长度100，必须唯一（不同学院不能重名）。
    name = models.CharField(max_length=100, unique=True)
    # 创建时间，自动设置为对象创建时的当前时间，不可修改。
    created_at = models.DateTimeField(auto_now_add=True)
    #  模型的元信息，设置在 Django 管理后台显示的名称，以及默认的排序方式。
    class Meta:
        verbose_name = "学院"
        verbose_name_plural = "学院"

    def __str__(self) -> str:
        return self.name

# 专业模型，表示学院下的专业，每个专业在同一学院内有一个唯一的名称。
class Major(models.Model):
    #College：关联的目标模型；
    # on_delete=models.CASCADE：级联删除，若学院被删除，关联的专业也会被删除；
    # related_name="majors"：反向关联名称，通过学院实例可通过college.majors.all()查询该学院下的所有专业。
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name="majors")
    # 专业名称，字符串类型，最大长度100，在同一学院内必须唯一（不同专业不能重名）。
    name = models.CharField(max_length=100)
    # 创建时间，自动设置为对象创建时的当前时间，不可修改。
    created_at = models.DateTimeField(auto_now_add=True)

    # 模型的元信息，设置在 Django 管理后台显示的名称，以及默认的排序方式
    # （先按学院ID排序，再按专业名称排序，最后按专业ID排序）。同时定义了一个联合唯一约束，确保同一学院内的专业名称唯一。
    class Meta:
        verbose_name = "专业"
        verbose_name_plural = "专业"
        constraints = [
            models.UniqueConstraint(fields=["college", "name"], name="uniq_major_college_name")
        ]
        ordering = ["college_id", "name", "id"]
    # 定义模型实例的字符串表示，返回格式为“学院名称 / 专业名称”，方便在管理后台和调试时查看对象信息。
    def __str__(self) -> str:
        return f"{self.college.name} / {self.name}"

# 班级模型，表示专业下的班级，每个班级在同一专业内有一个唯一的名称。
class ClassGroup(models.Model):
    # Major：关联的目标模型；
    # on_delete=models.CASCADE：级联删除，若专业被删除，关联的班级也会被删除；
    # related_name="classes"：反向关联名称，通过专业实例可通过major.classes.all()查询该专业下的所有班级。
    major = models.ForeignKey(Major, on_delete=models.CASCADE, related_name="classes")
    # 班级名称，字符串类型，最大长度100，在同一专业内必须唯一（不同班级不能重名）。
    name = models.CharField(max_length=100)
    # 创建时间，自动设置为对象创建时的当前时间，不可修改。
    created_at = models.DateTimeField(auto_now_add=True)
# 模型的元信息，设置在 Django 管理后台显示的名称，以及默认的排序方式
    class Meta:
        # verbose_name = "班级"：在管理后台显示的单数名称；
        #verbose_name是Django模型的元选项之一，用于指定在管理后台显示的单数名称。当你在管理后台查看某个模型的实例时，Django会使用verbose_name来显示该模型的名称。例如，如果verbose_name设置为"班级"，那么在管理后台中查看ClassGroup模型的实例时，会显示为"班级"而不是默认的"Class group"。
        # verbose_name_plural = "班级"：在管理后台显示的复数名称；
        # constraints：定义了一个联合唯一约束，确保同一专业内的班级名称唯一；
        # ordering：默认的排序方式，先按专业ID排序，再按班级名称排序，最后按班级ID排序。
        verbose_name = "班级"
        verbose_name_plural = "班级"
        constraints = [
            models.UniqueConstraint(fields=["major", "name"], name="uniq_class_major_name")
        ]
        ordering = ["major_id", "name", "id"]
    # 定义模型实例的字符串表示，返回格式为“专业名称 / 班级名称”，方便在管理后台和调试时查看对象信息。
    def __str__(self) -> str:
        return f"{self.major.name} / {self.name}"

# 用户模型，继承自 Django 的 AbstractUser，添加了角色、真实姓名、学院、专业、班级等字段。
class User(AbstractUser):
    # 定义用户角色的枚举类，使用 Django 的 TextChoices 
    # 来定义四种角色：学生、心理辅导员、二级学院管理员和系统管理员。
    class Role(models.TextChoices):
        STUDENT = "student", "学生"
        COUNSELOR = "counselor", "心理辅导员"
        COLLEGE_ADMIN = "college_admin", "二级学院管理员"
        SYS_ADMIN = "sys_admin", "系统管理员"
    # 用户模型的字段定义：
    # role：用户角色，字符串类型，选择范围由 Role 枚举定义，默认值为 Role.STUDENT（学生）；
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.STUDENT)
    # real_name：用户的真实姓名，字符串类型，最大长度64，可以为空；
    real_name = models.CharField(max_length=64, blank=True)
    # college：用户所属的学院，外键关联 College 模型，可以为空，删除学院时将该字段设置为 NULL，反向关联名称为 "users"（通过 college.users.all() 查询该学院下的所有用户）；
    college = models.ForeignKey(
        College, null=True, blank=True, on_delete=models.SET_NULL, related_name="users"
    )
    # major：用户所属的专业，外键关联 Major 模型，可以为空，删除专业时将该字段设置为 NULL，反向关联名称为 "users"（通过 major.users.all() 查询该专业下的所有用户）；
    major = models.ForeignKey(
        Major, null=True, blank=True, on_delete=models.SET_NULL, related_name="users"
    )
    # class_group：用户所属的班级，外键关联 ClassGroup 模型，可以为空，删除班级时将该字段设置为 NULL，反向关联名称为 "students"（通过 class_group.students.all() 查询该班级下的所有用户）；
    class_group = models.ForeignKey(
        ClassGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="students"
    )
    # student_no：学生学号，字符串类型，最大长度32，可以为空；
    student_no = models.CharField(max_length=32, blank=True)
    # phone：用户电话号码，字符串类型，最大长度32，可以为空；
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    # 定义模型实例的字符串表示，返回格式为“用户名（真实姓名）”，方便在管理后台和调试时查看对象信息。
    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT
    # 定义一些方便的属性方法来判断用户的角色，例如 is_counselor、is_college_admin 和 is_sys_admin，
    # 分别用于判断用户是否是心理辅导员、二级学院管理员和系统管理员。
    @property
    def is_counselor(self) -> bool:
        return self.role == self.Role.COUNSELOR

    @property
    def is_college_admin(self) -> bool:
        return self.role == self.Role.COLLEGE_ADMIN

    @property
    def is_sys_admin(self) -> bool:
        return self.role == self.Role.SYS_ADMIN

# 咨询师与学生的直接分配关系模型，表示某个咨询师直接负责某个学生。
class CounselorStudent(models.Model):
    # counselor：关联的咨询师，
    counselor = models.ForeignKey(
        User,#外键关联 User 模型
        on_delete=models.CASCADE,#删除咨询师时级联删除
        related_name="assigned_students",#反向关联名称为    
        limit_choices_to={"role": User.Role.COUNSELOR},#限制选择范围为 role=User.Role.COUNSELOR（只能选择心理辅导员角色的用户）
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_counselors",
        limit_choices_to={"role": User.Role.STUDENT},
    )
    # created_at：创建时间，自动设置为当前时间
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "咨询分配"
        verbose_name_plural = "咨询分配"
        # 定义一个联合唯一约束，确保同一个咨询师和学生的分配关系唯一（同一个咨询师不能重复分配同一个学生）。
        constraints = [
            models.UniqueConstraint(
                fields=["counselor", "student"], name="uniq_counselor_student"
            )
        ]
# 定义模型实例的字符串表示，返回格式为“咨询师用户名 -> 学生用户名”，方便在管理后台和调试时查看对象信息。
    def __str__(self) -> str:
        return f"{self.counselor.username} -> {self.student.username}"

# 咨询师与班级的分配关系模型，表示某个咨询师负责某个班级下的所有学生。
class CounselorClassAssignment(models.Model):
    counselor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_classes",
        limit_choices_to={"role": User.Role.COUNSELOR},
    )
    # class_group：关联的班级，外键关联 ClassGroup 模型，删除班级时级联删除，反向关联名称为 "assigned_counselors"（通过 class_group.assigned_counselors.all() 查询负责该班级的所有咨询师）。
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name="assigned_counselors")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "班级咨询分配"
        verbose_name_plural = "班级咨询分配"
        # 定义两个联合唯一约束：
        # 1. 确保同一个咨询师和班级的分配关系唯一（同一个咨询师不能重复分配同一个班级）。
        # 2. 确保同一个班级只能分配给一个咨询师（同一个班级不能有多个咨询师负责）。
        constraints = [
            models.UniqueConstraint(fields=["counselor", "class_group"], name="uniq_counselor_class"),
            models.UniqueConstraint(fields=["class_group"], name="uniq_class_one_counselor"),
        ]
    # 定义模型实例的字符串表示，返回格式为“咨询师用户名 -> 班级名称”，方便在管理后台和调试时查看对象信息。
    def __str__(self) -> str:
        return f"{self.counselor.username} -> {self.class_group.name}"
