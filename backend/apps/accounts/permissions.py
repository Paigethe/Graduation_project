from rest_framework.permissions import BasePermission
# 定义自定义权限类，分别用于判断用户是否具有系统管理员、学院管理员、心理辅导员和学生的权限，
# 以及组合权限（学院管理员或系统管理员、心理辅导员或系统管理员）。
#作用：这些权限类可以在视图中使用，以限制只有具有特定角色的用户才能访问某些接口或执行某些操作。

#判断用户是否具有系统管理员权限。
class IsSysAdmin(BasePermission):
    # has_permission 方法用于检查请求是否具有 访问权限。它从请求对象中获取用户信息，
    # 并检查用户是否经过身份验证且具有 is_sys_admin 属性为 True。
    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and getattr(user, "is_sys_admin", False))

#判断用户是否具有学院管理员权限。
class IsCollegeAdmin(BasePermission):
    # has_permission 方法用于检查请求是否具有访问权限。它从请求对象中获取用户信息，
    
    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)#获取请求对象中的用户信息，如果没有用户信息，则返回 None。
        return bool(# 并检查用户是否经过身份验证且具有 is_college_admin 属性为 True
            user and user.is_authenticated and getattr(user, "is_college_admin", False)
        )

#判断用户是否具有心理辅导员权限。
class IsCounselor(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and getattr(user, "is_counselor", False))

#判断用户是否具有学生权限。
class IsStudent(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and getattr(user, "is_student", False))

# 判断用户是否具有学院管理员或系统管理员权限。
class IsCollegeAdminOrSysAdmin(BasePermission):
    #
    def has_permission(self, request, view) -> bool:
        # 从请求对象中获取用户信息，并检查用户是否经过身份验证且具有 is_college_admin 或 is_sys_admin 属性为 True。
        user = getattr(request, "user", None)#获取请求对象中的用户信息，如果没有用户信息，则返回 None。
        if not user or not user.is_authenticated:
            return False
        return bool(getattr(user, "is_college_admin", False) or getattr(user, "is_sys_admin", False))

# 判断用户是否具有心理辅导员或系统管理员权限。
class IsCounselorOrSysAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return bool(getattr(user, "is_counselor", False) or getattr(user, "is_sys_admin", False))
