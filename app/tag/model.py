from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model

if TYPE_CHECKING:
    from app.diary.model import Diary  # 실제 Tag 모델이 정의된 경로에 맞춰 수정


class Tag(Model):
    id = fields.IntField(pk=True, generated=True)
    name = fields.CharField(max_length=50, unique=True)
    diaries: fields.ManyToManyRelation["Diary"]

    class Meta:
        table = "tags"
