from enum import StrEnum

from tortoise import fields
from tortoise.models import Model

from app.shared.model import TimestampMixin
from app.user.model import User


class AlertType(StrEnum):
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    SMS = "SMS"


class Notification(TimestampMixin, Model):
    alert_id = fields.BigIntField(pk=True)
    content = fields.CharField(max_length=255, null=True)
    alert_type = fields.CharEnumField(AlertType)

    user: fields.ManyToManyRelation["User"] = fields.ManyToManyField(
        "models.User", related_name="notifications", on_delete=fields.CASCADE
    )

    def __str__(self):
        return f"Notification(id={self.alert_id}, content={self.content})"

    class Meta:
        table = "감정 알림"
