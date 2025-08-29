import json
from typing import TYPE_CHECKING, Any, Optional

from tortoise import fields
from tortoise.models import Model

from app.ai.schema import MainEmotionType
from app.shared.model import TimestampMixin

if TYPE_CHECKING:
    from app.tag.model import Tag  # 실제 Tag 모델이 정의된 경로에 맞춰 수정
    from app.user.model import User  # 실제 User 모델이 정의된 경로에 맞춰 수정


class Diary(TimestampMixin, Model):
    id = fields.BigIntField(pk=True)

    # 자주 조회/정렬될 수 있으니 인덱스 부여
    title = fields.CharField(max_length=50, null=False, index=True)
    content = fields.TextField(null=False)

    # JSON 저장, 기본값은 None
    emotion_analysis: Optional[dict[str, Any]] = fields.JSONField(null=True)

    async def save(self, *args, **kwargs):
        if self.emotion_analysis is not None:
            if not isinstance(self.emotion_analysis, dict):
                raise ValueError("emotion_analysis는 dict(JSON object)만 허용합니다.")
            # 직렬화 가능성 추가 확인(키/값이 직렬화 가능해야 함)
            json.dumps(self.emotion_analysis, ensure_ascii=False)
        return await super().save(*args, **kwargs)

    main_emotion = fields.CharEnumField(enum_type=MainEmotionType, null=True)

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="diaries", on_delete=fields.CASCADE
    )
    images: fields.ReverseRelation["Image"]
    tags: fields.ManyToManyRelation["Tag"] = fields.ManyToManyField(
        "models.Tag",
        related_name="diaries",
        through="models.DiaryTag",  # 아래 명시적 through 모델 사용
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "diaries"

    def __str__(self):
        return f"Diary(id={self.id}, title={self.title}, emotion={self.main_emotion})"


class Image(Model):
    # Tortoise가 런타임에 만들어주는 FK 컬럼 힌트
    if TYPE_CHECKING:
        diary_id: int

    id = fields.BigIntField(pk=True)

    # 한 다이어리 내 표시 순서 → 인덱스 부여
    order = fields.IntField(null=False, index=True)
    image = fields.TextField(null=False)

    diary: fields.ForeignKeyRelation[Diary] = fields.ForeignKeyField(
        "models.Diary", related_name="images", on_delete=fields.CASCADE
    )

    class Meta:
        table = "images"
        # 같은 다이어리에서 동일 order 중복 방지
        unique_together = (("diary_id", "order"),)

    def __str__(self) -> str:
        return f"Image(id={self.id}, diary_id={self.diary_id}, order={self.order})"


class DiaryTag(Model):
    """
    Diary - Tag 조인 테이블.
    - 중복(같은 다이어리에 같은 태그) 방지
    - 조인/필터 성능을 위해 (diary_id, tag_id) 인덱스
    """

    diary: fields.ForeignKeyRelation[Diary] = fields.ForeignKeyField(
        "models.Diary", on_delete=fields.CASCADE
    )
    tag: fields.ForeignKeyRelation["Tag"] = fields.ForeignKeyField(
        "models.Tag", on_delete=fields.CASCADE
    )

    class Meta:
        table = "diary_tags"
        unique_together = (("diary_id", "tag_id"),)
        indexes = (("diary_id", "tag_id"),)

    def __str__(self) -> str:
        return f"DiaryTag(diary_id={self.diary.id}, tag_id={self.tag.tag_id})"
