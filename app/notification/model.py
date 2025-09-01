from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model

from app.shared.model import TimestampMixin

if TYPE_CHECKING:
    from app.user.model import User  # 실제 User 모델이 정의된 경로에 맞춰 수정


class NotificationType(StrEnum):
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    SMS = "SMS"


class Notification(TimestampMixin, Model):
    id = fields.BigIntField(pk=True)
    content = fields.CharField(max_length=255, null=True)
    type = fields.CharEnumField(NotificationType, default=NotificationType.EMAIL)

    # 타입 힌트는 문자열로 ("User") → 타입체커는 TYPE_CHECKING import 를 보고 인식
    user: fields.ManyToManyRelation["User"] = fields.ManyToManyField(
        "models.User",
        related_name="notifications",
        on_delete=fields.CASCADE,
        through="notification_users",
    )

    def __str__(self):
        return f"Notification(id={self.id}, content={self.content})"

    class Meta:
        table = "notifications"
