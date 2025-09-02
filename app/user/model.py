from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import Model, fields

from app.diary.model import MainEmotionType
from app.shared.model import TimestampMixin

if TYPE_CHECKING:
    from app.notification.model import Notification


class PeriodType(StrEnum):
    DAILY = "일간"
    WEEKLY = "주간"


class UserRole(StrEnum):
    USER = "user"
    STAFF = "staff"
    SUPERUSER = "superuser"


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
    user_roles = fields.CharEnumField(enum_type=UserRole, default=UserRole.USER)

    # Notification은 M2M (through 사용)
    notifications: fields.ManyToManyRelation["Notification"] = fields.ManyToManyField(
        "models.Notification",
        related_name="users",
        through="models.UserNotification",
    )

    # ✅ EmotionStats는 1:N의 역참조(ReverseRelation)여야 함
    emotion_stats: fields.ReverseRelation["EmotionStats"]

    class Meta:
        table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"User(id={self.id}, email={self.email})"


class EmotionStats(Model):
    stat_id = fields.IntField(pk=True, auto_increment=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        related_name="emotion_stats",  # ← User.emotion_stats 와 이름 일치
        on_delete=fields.CASCADE,
        index=True,
    )
    period_type = fields.CharEnumField(PeriodType)
    emotion_type = fields.CharEnumField(MainEmotionType)
    frequency = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "emotion_stats"


# ---------------------------------------------------------------------
# 유저 ↔ 알림 조인 테이블
# ---------------------------------------------------------------------
class UserNotification(Model):
    id = fields.IntField(pk=True)  # ✅ 명시 PK 추가(권장)

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User",
        related_name="user_notifications",
        on_delete=fields.CASCADE,
        index=True,
    )
    notification: fields.ForeignKeyRelation["Notification"] = fields.ForeignKeyField(
        "models.Notification",
        related_name="user_notifications",
        on_delete=fields.CASCADE,
        index=True,
    )

    class Meta:
        table = "user_notifications"
        unique_together = (("user", "notification"),)
        # ✅ 인덱스는 필드명 기준으로 선언
        indexes = (("user", "notification"),)

    # str 에러 해결용 type checking
    if TYPE_CHECKING:
        user_id: int
        notification_id: int

    def __str__(self) -> str:
        return f"UserNotification(user_id={self.user_id}, notification_id={self.notification_id})"  # FK 직접 접근
