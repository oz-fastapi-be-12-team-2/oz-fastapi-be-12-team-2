from tortoise import fields
from tortoise.models import Model
from app.diary.model import Diary

class Tag(Model):
    tag_id = fields.BigIntField(pk=True, generated=True)  # 태그 ID, AUTO_INCREMENT
    tag_name = fields.CharField(max_length=50, unique=True)

    diaries: fields.ManyToManyRelation["Diary"] = fields.ManyToManyField(
        "models.Diary",  # Diary 모델 참조
        related_name="tags",  # Diary에서 역참조 이름
        through="diary_tags"  # 중간 테이블 이름
    )

    class Meta:
        table = "tags"
