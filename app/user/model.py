from enum import Enum, StrEnum
from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model

from app.shared.model import TimestampMixin

if TYPE_CHECKING:
    from app.notification.model import Notification


# User 관련 Enum
class UserRole(StrEnum):
    USER = "user"
    STAFF = "staff"
    SUPERUSER = "superuser"


class NotificationType(StrEnum):
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    SMS = "SMS"


# EmotionStats 관련 Enum
class PeriodType(str, Enum):
    DAILY = "일간"
    WEEKLY = "주간"


class EmotionType(str, Enum):
    JOY = "기쁨"
    ANGER = "분노"
    SADNESS = "우울"


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
    notification_type = fields.CharEnumField(
        enum_type=NotificationType, default=NotificationType.PUSH
    )
    user_roles = fields.CharEnumField(enum_type=UserRole, default=UserRole.USER)

    notifications: fields.ManyToManyRelation["Notification"]

    class Meta:
        table = "users"
        ordering = ["-created_at"]


# EmotionStats 필드
class EmotionStats(Model):
    stat_id = fields.IntField(pk=True, auto_increment=True)
    user = fields.ForeignKeyField("models.User", related_name="emotion_stats")
    period_type = fields.CharEnumField(enum_type=PeriodType)
    emotion_type = fields.CharEnumField(enum_type=EmotionType)
    frequency = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "emotion_stats"
