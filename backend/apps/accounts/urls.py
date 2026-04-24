# accounts/urls.py
# 该文件定义了 accounts 应用的 URL 路由，
# 使用 Django REST Framework 的 DefaultRouter 来自动生成标准的 RESTful API 路径，
# 并且还定义了一些自定义的路径用于特定的视图。    
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminUserViewSet,
    ClassGroupViewSet,
    CollegeViewSet,
    CounselorClassAssignmentViewSet,
    CounselorStudentsView,
    CounselorStudentViewSet,
    MajorViewSet,
    MeView,
    RegisterStudentView,
    StudentProfileView,
)
# 使用 DefaultRouter 来注册视图集，自动生成标准的 RESTful API 路径。
router = DefaultRouter()
# 注册视图集到路由器，指定 URL 前缀和视图集类，以及可选的 basename 用于反向 URL 解析。
router.register(r"colleges", CollegeViewSet, basename="college")
router.register(r"majors", MajorViewSet, basename="major")
router.register(r"classes", ClassGroupViewSet, basename="class-group")
router.register(r"admin/users", AdminUserViewSet, basename="admin-user")
router.register(r"admin/assignments", CounselorStudentViewSet, basename="admin-assignment")
router.register(r"admin/class-assignments", CounselorClassAssignmentViewSet, basename="admin-class-assignment")
# 定义 URL 模式列表，包含了通过路由器自动生成的路径，以及一些自定义的路径。
urlpatterns = [
    path("", include(router.urls)),
    path("auth/register/", RegisterStudentView.as_view(), name="register-student"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("counselor/students/", CounselorStudentsView.as_view(), name="counselor-students"),
    path("students/<int:pk>/profile/", StudentProfileView.as_view(), name="student-profile"),
]
