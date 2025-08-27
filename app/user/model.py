from enum import StrEnum

from tortoise import fields
from tortoise.models import Model

from app.shared.models import TimestampMixin


class UserRole(StrEnum):
    USER = "user"
    STAFF = "staff"
    SUPERUSER = "superuser"


class User(TimestampMixin, Model):
    id = fields.BigIntField(pk=True, generated=True)  # 사용자 ID, AUTO_INCREMENT
    nickname = fields.CharField(max_length=20, unique=True)  # 로그인 ID
    email = fields.CharField(max_length=100, unique=True)  # 이메일
    password = fields.CharField(max_length=255)  # 패스워드
    username = fields.CharField(max_length=20)  # 이름
    phonenumber = fields.CharField(max_length=20)  # 연락처
    lastlogin = fields.DatetimeField(null=True)  # 마지막 로그인
    account_activation = fields.BooleanField(default=False)  # 계정 활성화 여부
    user_roles = fields.CharEnumField(
        enum_type=UserRole, default=UserRole.USER
    )  # 유저 권한

    class Meta:
        table = "users"
        ordering = ["-created_at"]
