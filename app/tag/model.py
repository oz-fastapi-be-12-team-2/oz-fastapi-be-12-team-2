from tortoise import fields
from tortoise.models import Model

from app.diary.model import Diary


class Tag(Model):
    tag_id = fields.BigIntField(pk=True, generated=True)  # 태그 ID, AUTO_INCREMENT
    tag_name = fields.CharField(max_length=50, unique=True)

    diaries: fields.ManyToManyRelation["Diary"]

    class Meta:
        table = "tags"
