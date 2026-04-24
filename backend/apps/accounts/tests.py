
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import College
# 该测试类用于验证咨询教师分配的逻辑，确保同一学院的学生只能分配给同一学院的咨询教师。
User = get_user_model()

# 用于验证咨询教师分配的逻辑，确保同一学院的学生只能分配给同一学院的咨询教师。  
class CounselorAssignmentValidationTests(APITestCase):
    # 在测试开始前设置测试数据，包括两个学院、一个系统管理员、一个咨询教师和两个学生（分别属于不同学院）。
    def setUp(self):
        self.college_a = College.objects.create(name="学院A")
        self.college_b = College.objects.create(name="学院B")

        self.sys_admin = User.objects.create_user(
            username="sys_admin_test",
            password="123456",
            role=User.Role.SYS_ADMIN,
        )
        self.counselor = User.objects.create_user(
            username="counselor_a",
            password="123456",
            role=User.Role.COUNSELOR,
            college=self.college_a,
        )
        self.student_a = User.objects.create_user(
            username="student_a",
            password="123456",
            role=User.Role.STUDENT,
            college=self.college_a,
        )
        self.student_b = User.objects.create_user(
            username="student_b",
            password="123456",
            role=User.Role.STUDENT,
            college=self.college_b,
        )
        self.client.force_authenticate(self.sys_admin)
# 测试方法 test_reject_cross_college_assignment 用于验证跨学院分配的拒绝逻辑，尝试将学院B的学生分配给学院A的咨询教师，预期返回 400 错误，并且错误信息中包含 "同一学院" 的提示。
    def test_reject_cross_college_assignment(self):
        resp = self.client.post(
            "/api/admin/assignments/",
            {"counselor_id": self.counselor.id, "student_id": self.student_b.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("同一学院", str(resp.data))
# 测试方法 test_allow_same_college_assignment 用于验证同学院分配的允许逻辑，尝试将学院A的学生分配给学院A的咨询教师，预期返回 201 成功，并且返回的数据中包含正确的咨询教师和学生ID。
    def test_allow_same_college_assignment(self):
        resp = self.client.post(
            "/api/admin/assignments/",
            {"counselor_id": self.counselor.id, "student_id": self.student_a.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["counselor"]["id"], self.counselor.id)
        self.assertEqual(resp.data["student"]["id"], self.student_a.id)
