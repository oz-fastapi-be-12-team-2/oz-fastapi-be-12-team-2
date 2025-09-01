from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import Model, fields

from app.diary.model import MainEmotionType
from app.notification.model import NotificationType
from app.shared.model import TimestampMixin

if TYPE_CHECKING:
    from app.notification.model import (  # 실제 Notification 모델이 정의된 경로에 맞춰 수정
        Notification,
    )


class PeriodType(StrEnum):
    DAILY = "일간"
    WEEKLY = "주간"


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
    receive_notifications = fields.BooleanField(default=True)
    notification_type = fields.CharEnumField(
        enum_type=NotificationType, default=NotificationType.PUSH
    )
    user_roles = fields.CharEnumField(
        enum_type=UserRole, default=UserRole.USER
    )  # 유저 권한

    notifications: fields.ManyToManyRelation["Notification"]
    emotionstats: fields.ManyToManyRelation["EmotionStats"]

    class Meta:
        table = "users"
        ordering = ["-created_at"]


# EmotionStats 필드 (확인필요)
class EmotionStats(Model):
    stat_id = fields.IntField(pk=True)  # AUTO_INCREMENT PK
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="emotion_stats"
    )  # FK
    period_type = fields.CharEnumField(PeriodType)  # ENUM
    emotion_type = fields.CharEnumField(MainEmotionType)  # ENUM
    frequency = fields.IntField()  # 횟수
    created_at = fields.DatetimeField(auto_now_add=True)  # 생성시 자동 입력

    class Meta:
        table = "emotion_stats"
