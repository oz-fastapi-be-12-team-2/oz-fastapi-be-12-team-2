from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model

if TYPE_CHECKING:
    from app.user.model import User  # 실제 User 모델이 정의된 경로에 맞춰 수정


class NotificationType(StrEnum):
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    SMS = "SMS"


class Notification(Model):
    id = fields.BigIntField(pk=True, generated=True)
    weekday = fields.IntField()  # 요일 필드 추가
    content = fields.CharField(max_length=255)  # nullable false
    notification_type = fields.CharEnumField(
        NotificationType, max_length=5, default=NotificationType.EMAIL
    )  # 최대 길이 추가

    # 타입 힌트는 문자열로 ("User") → 타입체커는 TYPE_CHECKING import 를 보고 인식
    users: fields.ManyToManyRelation["User"]

    def __str__(self):
        return f"Notification(id={self.id}, weekday={self.weekday}, type={self.notification_type})"  # weekday 추가

    class Meta:
        table = "notifications"
        unique_together = ("weekday", "notification_type")  # unique 설정 추가
