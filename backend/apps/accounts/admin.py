# 注册了 6 个 数据模型的管理界面，账号管理模块
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import ClassGroup, College, CounselorClassAssignment, CounselorStudent, Major, User


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):# 注册College模型到Admin后台
    list_display = ("id", "name", "created_at")


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "college", "created_at")
    list_filter = ("college",)


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "major", "created_at")
    list_filter = ("major__college", "major")# 筛选条件：按“专业所属学院”、“所属专业”筛选


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # 自定义用户编辑页的字段分组（继承Django内置UserAdmin的分组，新增“扩展信息”分组）
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "扩展信息",
            {
                "fields": (
                    "role",
                    "real_name",
                    "college",
                    "major",
                    "class_group",
                    "student_no",
                    "phone",
                )
            },
        ),
    )
    # 列表页展示字段：ID、用户名、真实姓名、角色、学院、专业、班级、是否为工作人员
    list_display = ("id", "username", "real_name", "role", "college", "major", "class_group", "is_staff")
    # 列表页筛选条件：角色、学院、专业、班级、是否为工作人员、是否为超级管理员
    list_filter = ("role", "college", "major", "class_group", "is_staff", "is_superuser")


@admin.register(CounselorStudent)
class CounselorStudentAdmin(admin.ModelAdmin):
    list_display = ("id", "counselor", "student", "created_at")
    list_filter = ("counselor",)


@admin.register(CounselorClassAssignment)
class CounselorClassAssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "counselor", "class_group", "created_at")
    list_filter = ("counselor", "class_group__major__college", "class_group__major")
# 它是 Django 项目的「后台管理界面配置文件」，
# 专门用来定义：管理员在网站后台能看到什么、能操作什么、怎么展示数据。
# 让管理员可以在浏览器后台，可视化管理 学院、专业、班级、用户、辅导员分配 等所有数据，不用写前端页面。