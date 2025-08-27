from enum import StrEnum

from tortoise import fields
from tortoise.models import Model

from app.shared.models import TimestampMixin


class AlertType(StrEnum):
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    SMS = "SMS"


class Notification(Model, TimestampMixin):
    alert_id = fields.BigIntField(pk=True)
    content = fields.CharField(max_length=255)
    alert_type = fields.CharEnumField(AlertType)


class Meta:
    table = "감정 알림"
