from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import Model, fields

from app.diary.model import MainEmotionType
from app.shared.model import TimestampMixin

if TYPE_CHECKING:
    from app.notification.model import (  # 실제 Notification 모델이 정의된 경로에 맞춰 수정
        Notification,
    )


class PeriodType(StrEnum):
    DAILY = "일간"
    WEEKLY = "주간"


# User 관련 Enum
class UserRole(StrEnum):
    USER = "user"
    STAFF = "staff"
    SUPERUSER = "superuser"


# User 필드
class User(TimestampMixin, Model):
    id = fields.BigIntField(pk=True, generated=True)
    nickname = fields.CharField(max_length=20, unique=True)
    email = fields.CharField(max_length=100, unique=True)
    password = fields.CharField(max_length=255)
    username = fields.CharField(max_length=20)
    phonenumber = fields.CharField(max_length=20)
    lastlogin = fields.DatetimeField(null=True)
    account_activation = fields.BooleanField(default=False)
    receive_notifications = fields.BooleanField(default=True)
    user_roles = fields.CharEnumField(
        enum_type=UserRole, default=UserRole.USER
    )  # 유저 권한

    notifications: fields.ManyToManyRelation["Notification"] = fields.ManyToManyField(
        "models.Notification",
        related_name="users",
        through="models.UserNotification",  # ← 조인 모델 경로
    )
    emotionstats: fields.ManyToManyRelation["EmotionStats"]

    class Meta:
        table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"User(id={self.id}, email={self.email}, notifications_type={self.notifications})"


# EmotionStats 필드
class EmotionStats(Model):
    stat_id = fields.IntField(pk=True, auto_increment=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="emotion_stats"
    )  # FK

    period_type = fields.CharEnumField(PeriodType)  # ENUM
    emotion_type = fields.CharEnumField(MainEmotionType)  # ENUM
    frequency = fields.IntField()  # 횟수
    created_at = fields.DatetimeField(auto_now_add=True)  # 생성시 자동 입력

    class Meta:
        table = "emotion_stats"


# ---------------------------------------------------------------------
# 유저 알람 조인 모델
# ---------------------------------------------------------------------


class UserNotification(Model):
    """
    유저 - 알람 조인 테이블.
    - 중복(같은 다이어리에 같은 태그) 방지
    - 조인/필터 성능을 위해 (diary_id, tag_id) 인덱스
    """

    id = fields.IntField(pk=True, generated=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
    )
    notification: fields.ForeignKeyRelation[Notification] = fields.ForeignKeyField(
        "models.Notification",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "user_notification"
        unique_together = (("user", "notification"),)
        indexes = (("user", "notification"),)

    def __str__(self) -> str:
        return f"UserNotification(user_id={self.user.id}, notification_id={self.notification.id})"
