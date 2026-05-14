# serializers.py 定义了用于序列化和反序列化数据的类，这些类将 Django 模型实例转换为 JSON 格式，
# 或者将 JSON 数据转换为 Django 模型实例，以便在 API 视图中使用。
# 这些序列化器类继承自 rest_framework.serializers.ModelSerializer，
# 并且定义了与模型对应的字段和验证逻辑，以确保数据的正确性和完整性。
# 这些序列化器在视图中被用来处理请求和响应的数据格式，确保前端和后端之间的数据交换符合预期的结构和要求。

# 将 Django 模型对象转换为 JSON 结构
# 将前端提交的 JSON 数据验证并转换为 Django 模型字段
# 处理用户注册、学生/咨询师分配、专业/班级创建等 API 数据验证逻辑
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import ClassGroup, College, CounselorClassAssignment, CounselorStudent, Major
# 获取当前项目中使用的用户模型，通常是自定义的 User 模型。通过 get_user_model() 函数，
User = get_user_model()

# 定义了多个序列化器类，用于处理不同的模型和数据验证需求。
# CollegeSerializer：用于序列化 College 模型，包含 id 和 name 字段。
class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College#指定该序列化器对应的 Django 模型为 College。
        #指定在序列化和反序列化过程中要包含的字段列表。这些字段将被转换为 JSON 格式进行输出，或者从 JSON 数据中提取进行输入验证。
        fields = ["id", "name"]

# MajorSerializer：用于序列化 Major 模型，包含 id、name、college（嵌套的 CollegeSerializer）和 created_at 字段。
class MajorSerializer(serializers.ModelSerializer):
    # college 字段使用 CollegeSerializer 进行嵌套序列化，设置为只读（read_only=True），
    # 表示在反序列化时  不需要提供该字段的输入，而是在序列化输出时包含该字段的详细信息。
    college = CollegeSerializer(read_only=True)

    # 定义模型的元信息，指定关联的模型为 Major，以及要包含的字段列表。
    class Meta:
        # model = Major：指定该序列化器对应的 Django 模型为 Major。
        model = Major
        # fields = ["id", "name", "college", "created_at"]：指定在序列化和反序列化过程中要包含的字段列表。
        # 这些字段将被转换为 JSON 格式进行输出，或者从 JSON 数据中提取进行输入验证。
        fields = ["id", "name", "college", "created_at"]

# ClassGroupSerializer：用于序列化 ClassGroup 模型，包含 id、name、major（嵌套的 MajorSerializer）和 created_at 字段。
class ClassGroupSerializer(serializers.ModelSerializer):
    major = MajorSerializer(read_only=True)

    class Meta:
        model = ClassGroup
        fields = ["id", "name", "major", "created_at"]

# 用于序列化当前用户信息，包含 id、username、real_name、role、college（嵌套的 CollegeSerializer）、major（嵌套的 MajorSerializer）和 class_group（嵌套的 ClassGroupSerializer）字段。
class UserMeSerializer(serializers.ModelSerializer):
    # 表示在反序列化时  不需要提供该字段的输入，而是在序列化输出时包含该字段的详细信息。
    college = CollegeSerializer(read_only=True)
    major = MajorSerializer(read_only=True)
    class_group = ClassGroupSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "real_name", "role", "college", "major", "class_group"]

# 用于学生注册的序列化器，
# 以及相关的验证逻辑，确保用户名唯一、学院存在、专业和班级与学院的关系正确等。
class RegisterStudentSerializer(serializers.ModelSerializer):
    password = serializers.CharField(min_length=6, write_only=True)
    college_id = serializers.IntegerField(required=True, write_only=True)
    major_id = serializers.IntegerField(required=True, write_only=True)
    class_group_id = serializers.IntegerField(required=True, write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "real_name",
            "college_id",
            "major_id",
            "class_group_id",
            "student_no",
            "role",
        ]
        read_only_fields = ["id", "role"]
# 定义了多个验证方法
## 验证用户名是否唯一，确保提供的用户名在数据库中不存在。如果用户名已存在，抛出一个 ValidationError 异常，提示 "用户名已存在"。
    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value
# 验证学院ID是否有效，确保提供的学院ID在数据库中存在。如果学院ID无效，抛出一个 ValidationError 异常，提示 "无效的学院"。
    def validate_college_id(self, value: int) -> int:
        if not College.objects.filter(id=value).exists():
            raise serializers.ValidationError("无效的学院")
        return value
# validate 方法用于进行跨字段验证，确保专业和班级与学院的关系正确。    
    def validate(self, attrs):
        college_id = attrs.get("college_id")
        major_id = attrs.get("major_id")
        class_group_id = attrs.get("class_group_id")

        college = College.objects.filter(id=college_id).first()
        if not college:
            raise serializers.ValidationError("无效的学院")

        major = Major.objects.filter(id=major_id, college_id=college_id).first()
        if not major:
            raise serializers.ValidationError({"major_id": "专业不存在或不属于当前学院"})

        class_group = ClassGroup.objects.filter(id=class_group_id, major_id=major_id).first()
        if not class_group:
            raise serializers.ValidationError({"class_group_id": "班级不存在或不属于当前专业"})

        return attrs
    
# create 方法用于创建一个新的 User 实例。
# 它从 validated_data 中提取 college_id、major_id、class_group_id 和 password 字段，
# 并根据这些字段查询对应的 College、Major 和 ClassGroup 对象。然后创建一个新的
    def create(self, validated_data):
        college_id = validated_data.pop("college_id")
        college = College.objects.get(id=college_id)
        major_id = validated_data.pop("major_id")
        class_group_id = validated_data.pop("class_group_id")
        password = validated_data.pop("password")

        major = Major.objects.get(id=major_id)
        class_group = ClassGroup.objects.get(id=class_group_id)

        user = User(
            **validated_data,
            role=User.Role.STUDENT,
            college=college,
            major=major,
            class_group=class_group,
        )
        user.set_password(password)
        user.last_login = timezone.now()  # 设置注册时间为最后登录时间，避免新用户被标记为"从未登录"
        user.save()
        return user

# 用于管理员创建用户的序列化器，包含更多字段和更复杂的验证逻辑，
# 允许管理员指定用户的角色、学院、专业和班级等信息，并确保这些信息之间的关系正确。
class AdminCreateUserSerializer(serializers.ModelSerializer):
    # 定义一个 password 字段，要求最小长度为 6，并且设置为 write_only=True
    # 表示该字段仅用于输入验证，不会在序列化输出中包含。
    password = serializers.CharField(min_length=6, write_only=True)
    # 定义 college_id、major_id 和 class_group_id 字段，
    # 分别用于接收学院、专业和班级的 ID。
    # 这些字段都是可选的（required=False），允许为 null（allow_null=True）
    college_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    major_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    class_group_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    college = CollegeSerializer(read_only=True)
    major = MajorSerializer(read_only=True)
    class_group = ClassGroupSerializer(read_only=True)
# 定义模型的元信息，指定关联的模型为 User，以及要包含的字段列表。
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "real_name",
            "role",
            "college_id",
            "college",
            "major_id",
            "major",
            "class_group_id",
            "class_group",
            "student_no",
            "phone",
        ]
# 定义多个验证方法，确保输入数据的正确性和一致性。
    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value

    def validate_college_id(self, value: int | None) -> int | None:
        if value is None:
            return None
        if not College.objects.filter(id=value).exists():
            raise serializers.ValidationError("无效的学院")
        return value
    
# validate 方法用于进行跨字段验证，确保专业和班级与学院的关系正确。
    def validate(self, attrs):
        role = attrs.get("role")
        college_id = attrs.get("college_id")
        major_id = attrs.get("major_id")
        class_group_id = attrs.get("class_group_id")
        # 根据提供的 major_id 和 class_group_id 分别查询 Major 和 ClassGroup 模型，获取对应的对象。
        major = Major.objects.filter(id=major_id).first() if major_id else None
        class_group = ClassGroup.objects.select_related("major").filter(id=class_group_id).first() if class_group_id else None

        # 学生、咨询师和学院管理员必须绑定学院，
        # 如果没有提供 college_id，抛出一个 ValidationError 异常，提示 "该角色必须绑定学院"。 
        if role in {User.Role.STUDENT, User.Role.COUNSELOR, User.Role.COLLEGE_ADMIN} and college_id is None:
            raise serializers.ValidationError({"college_id": "该角色必须绑定学院"})
        if major and college_id and major.college_id != college_id:
            raise serializers.ValidationError({"major_id": "专业不属于当前学院"})
        if class_group:
            if major and class_group.major_id != major.id:
                raise serializers.ValidationError({"class_group_id": "班级不属于当前专业"})
            if college_id and class_group.major.college_id != college_id:
                raise serializers.ValidationError({"class_group_id": "班级不属于当前学院"})
            attrs["major_id"] = class_group.major_id
            # 如果提供了班级信息，但没有提供学院信息，则从班级关联的专业中获取学院信息，确保用户的学院与班级所属的学院一致。
            if college_id is None:
                attrs["college_id"] = class_group.major.college_id
        # 如果提供了专业信息，但没有提供学院信息，则从专业关联的学院中获取学院信息，确保用户的学院与专业所属的学院一致。
        if major and college_id is None:
            attrs["college_id"] = major.college_id
        return attrs
# create 方法用于创建一个新的 User 实例。
# 它从 validated_data 中提取 college_id、major_id、class_group_id 和 password 字段，
# 并根据这些字段查询对应的 College、Major 和 ClassGroup 对象。然后创建一个新的 User 实例，
# 使用解包操作符 ** 将 validated_data 中剩余的字段作为参数传递给 User 构造函数，
# 同时设置关联的 college、major 和 class_group 对象。最后设置用户密码，并保存用户对象到数据库中。
# 返回创建的用户对象。用于管理员创建用户时使用，允许指定更多字段和更复杂的验证逻辑。
    def create(self, validated_data):
        college_id = validated_data.pop("college_id", None)
        major_id = validated_data.pop("major_id", None)
        class_group_id = validated_data.pop("class_group_id", None)
        password = validated_data.pop("password")
        college = College.objects.get(id=college_id) if college_id is not None else None
        major = Major.objects.filter(id=major_id).first() if major_id else None
        class_group = ClassGroup.objects.filter(id=class_group_id).first() if class_group_id else None
        user = User(**validated_data, college=college, major=major, class_group=class_group)
        user.set_password(password)
        user.save()
        return user

# 用于序列化 CounselorStudent 模型
class CounselorStudentSerializer(serializers.ModelSerializer):
    counselor_id = serializers.IntegerField(write_only=True)
    student_id = serializers.IntegerField(write_only=True)
    counselor = UserMeSerializer(read_only=True)
    student = UserMeSerializer(read_only=True)

    class Meta:
        model = CounselorStudent
        fields = ["id", "counselor_id", "student_id", "counselor", "student", "created_at"]

# validate 方法用于验证咨询教师和学生的关系，确保他们都存在且属于同一学院。
    def validate(self, attrs):
        # 根据提供的 counselor_id 和 student_id 分别查询 User 模型，获取对应的咨询教师和学生对象。
        counselor = User.objects.filter(id=attrs["counselor_id"]).first()
        student = User.objects.filter(id=attrs["student_id"]).first()
        # 验证咨询教师和学生是否存在，并且角色是否正确。如果咨询教师不存在或角色不为 COUNSELOR，抛出一个 ValidationError 异常，提示 "无效的咨询教师"。
        if not counselor or counselor.role != User.Role.COUNSELOR:
            raise serializers.ValidationError({"counselor_id": "无效的咨询教师"})
        if not student or student.role != User.Role.STUDENT:
            raise serializers.ValidationError({"student_id": "无效的学生"})
        if counselor.college_id is None or student.college_id is None:
            raise serializers.ValidationError("咨询教师和学生都必须先绑定学院")
        if counselor.college_id != student.college_id:
            raise serializers.ValidationError("咨询教师与学生必须属于同一学院")
        return attrs

    def create(self, validated_data):
        counselor = User.objects.get(id=validated_data["counselor_id"])
        student = User.objects.get(id=validated_data["student_id"])
        obj, _created = CounselorStudent.objects.get_or_create(
            counselor=counselor, student=student
        )
        return obj

# 用于序列化 CounselorClassAssignment 模型，
class MajorCreateSerializer(serializers.ModelSerializer):
    college_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Major
        fields = ["id", "name", "college_id", "created_at"]
        read_only_fields = ["id", "created_at"]
# validate_college_id 方法用于验证提供的学院ID是否有效，确保该学院ID在数据库中存在。如果学院ID无效，抛出一个 ValidationError 异常，提示 "无效学院"。
    def validate_college_id(self, value: int) -> int:
        if not College.objects.filter(id=value).exists():
            raise serializers.ValidationError("无效学院")
        return value

    def create(self, validated_data):
        college = College.objects.get(id=validated_data.pop("college_id"))
        return Major.objects.create(college=college, **validated_data)

# 用于序列化 CounselorClassAssignment 模型，
# 包含验证逻辑，确保咨询教师和班级的关系正确，并且同一班级只能分配给一个咨询教师。
class ClassGroupCreateSerializer(serializers.ModelSerializer):
    major_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ClassGroup
        fields = ["id", "name", "major_id", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_major_id(self, value: int) -> int:
        if not Major.objects.filter(id=value).exists():
            raise serializers.ValidationError("无效专业")
        return value

    def create(self, validated_data):
        major = Major.objects.get(id=validated_data.pop("major_id"))
        return ClassGroup.objects.create(major=major, **validated_data)

# 用于序列化 CounselorClassAssignment 模型，包含验证逻辑，
# 确保咨询教师和班级的关系正确，并且同一班级只能分配给一个咨询教师。
class CounselorClassAssignmentSerializer(serializers.ModelSerializer):
    counselor_id = serializers.IntegerField(write_only=True)
    class_group_id = serializers.IntegerField(write_only=True)
    counselor = UserMeSerializer(read_only=True)
    class_group = ClassGroupSerializer(read_only=True)

    class Meta:
        model = CounselorClassAssignment
        fields = ["id", "counselor_id", "class_group_id", "counselor", "class_group", "created_at"]
# validate 方法用于验证咨询教师和班级的关系，确保他们都存在且属于同一学院，
# 并且同一班级只能分配给一个咨询教师。
    def validate(self, attrs):
        # 根据提供的 counselor_id 和 class_group_id 分别查询 User 模型和 ClassGroup 模型，
        # 获取对应的咨询教师和班级对象。
        counselor = User.objects.filter(id=attrs["counselor_id"], role=User.Role.COUNSELOR).first()
        class_group = ClassGroup.objects.select_related("major").filter(id=attrs["class_group_id"]).first()
        if not counselor:
            raise serializers.ValidationError({"counselor_id": "无效的咨询教师"})
        if not class_group:
            raise serializers.ValidationError({"class_group_id": "无效班级"})
        if counselor.college_id is None:
            raise serializers.ValidationError({"counselor_id": "咨询教师未绑定学院"})
        if class_group.major.college_id != counselor.college_id:
            raise serializers.ValidationError("咨询教师与班级必须属于同一学院")
        if CounselorClassAssignment.objects.filter(class_group=class_group).exclude(counselor=counselor).exists():
            raise serializers.ValidationError({"class_group_id": "该班级已分配给其他咨询教师"})
        return attrs

    def create(self, validated_data):
        counselor = User.objects.get(id=validated_data["counselor_id"])
        class_group = ClassGroup.objects.get(id=validated_data["class_group_id"])
        obj, _created = CounselorClassAssignment.objects.get_or_create(
            counselor=counselor, class_group=class_group
        )
        return obj
