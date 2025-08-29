from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model

from app.shared.model import TimestampMixin

if TYPE_CHECKING:
    from app.tag.model import Tag
    from app.user.model import User


class MainEmotion(StrEnum):
    POSITIVE = "긍정"
    NEGATIVE = "부정"
    NEUTRAL = "중립"


class Diary(TimestampMixin, Model):
    id = fields.BigIntField(pk=True)
    title = fields.CharField(max_length=50, null=False)
    content = fields.TextField(null=False)

    emotion_analysis = fields.TextField(null=True)
    main_emotion = fields.CharEnumField(enum_type=MainEmotion, null=True)  # ENUM

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="diaries", on_delete=fields.CASCADE
    )
    images: fields.ReverseRelation["Image"]
    tags: fields.ManyToManyRelation["Tag"] = fields.ManyToManyField(
        "models.Tag", related_name="diaries", through="diary_tag"
    )

    class Meta:
        table = "diaries"

    def __str__(self):
        return f"Diary(id={self.id}, title={self.title}, emotion={self.main_emotion})"


class Image(Model):
    id = fields.BigIntField(pk=True)
    order = fields.IntField(null=False)
    image = fields.TextField(null=False)

    diary: fields.ForeignKeyRelation[Diary] = fields.ForeignKeyField(
        "models.Diary", related_name="images", on_delete=fields.CASCADE
    )

    class Meta:
        table = "images"

    def __str__(self):
        return f"Image(id={self.id}, diary_id={self.diary_id})"
