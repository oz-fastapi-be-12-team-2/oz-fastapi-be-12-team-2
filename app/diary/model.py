from __future__ import annotations

import json
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Optional

from tortoise import fields
from tortoise.models import Model

from app.shared.model import TimestampMixin

if TYPE_CHECKING:
    from app.tag.model import Tag  # 실제 Tag 모델이 정의된 경로에 맞춰 수정
    from app.user.model import User  # 실제 User 모델이 정의된 경로에 맞춰 수정


class MainEmotionType(StrEnum):
    POSITIVE = "긍정"
    NEGATIVE = "부정"
    NEUTRAL = "중립"


# ---------------------------------------------------------------------
# 다이어리 모델
# ---------------------------------------------------------------------


class Diary(TimestampMixin, Model):
    id = fields.BigIntField(pk=True)

    # 자주 조회/정렬될 수 있으니 인덱스 부여
    title = fields.CharField(max_length=50, null=False, index=True)
    content = fields.TextField(null=False)
    # AI 감정 분석 리포트(JSON) 예시
    # {
    #   "main_emotion": "긍정" | "부정" | "중립",   # MainEmotionType (주요 감정)
    #   "confidence": 0.0 ~ 1.0,                  # 분석 신뢰도(0~1)
    #   "emotion_analysis_report": {                      # 상세 분석 결과
    #     "reason": "감정 판단의 근거 텍스트",        # Optional
    #     "key_phrases": ["핵심", "키워드", "..."]    # 문자열 배열
    #   }
    # }
    emotion_analysis_report: Optional[dict[str, Any]] = fields.JSONField(
        null=True,
        description=(
            "AI 감정 분석 리포트(JSON: main_emotion, confidence, "
            "emotion_analysis{reason,key_phrases})"
        ),
    )

    async def save(self, *args, **kwargs):
        """
        JSONField에 'JSON object(dict)'만 저장되도록 가드.
        (배열/문자열/숫자 등은 허용하지 않음)
        """
        v = self.emotion_analysis_report
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError(
                    "emotion_analysis_report는 dict(JSON object)만 허용합니다."
                )
            # 직렬화 가능성 추가 확인(키/값이 JSON 직렬화 가능해야 함)
            json.dumps(v, ensure_ascii=False)
        return await super().save(*args, **kwargs)

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="diaries", on_delete=fields.CASCADE
    )
    images: fields.ReverseRelation["Image"]
    tags: fields.ManyToManyRelation["Tag"] = fields.ManyToManyField(
        "models.Tag",
        related_name="diaries",  # Tag → diaries 로 접근
        through="models.DiaryTag",
    )

    class Meta:
        table = "diaries"

    def __str__(self):
        return f"title={self.title}, emotion_analysis_report={self.emotion_analysis_report})"


# ---------------------------------------------------------------------
# 이미지 모델
# ---------------------------------------------------------------------


class Image(Model):

    id = fields.BigIntField(pk=True, generated=True)

    # 한 다이어리 내 표시 순서 → 인덱스 부여
    order = fields.IntField(null=False, index=True)
    url = fields.TextField(null=False)

    diary: fields.ForeignKeyRelation["Diary"] = fields.ForeignKeyField(
        "models.Diary",
        related_name="images",
        on_delete=fields.CASCADE,
        db_index=True,
    )

    class Meta:
        table = "images"
        # 같은 다이어리에서 동일 order 중복 방지
        unique_together = (("diary_id", "order"),)

    # def __str__(self) -> str:
    #     return f"Image(id={self.id}, diary_id={self.diary.id}, order={self.order})"


# ---------------------------------------------------------------------
# 다이어리_태그 조인 모델
# ---------------------------------------------------------------------


class DiaryTag(Model):
    """
    Diary - Tag 조인 테이블.
    - 중복(같은 다이어리에 같은 태그) 방지
    - 조인/필터 성능을 위해 (diary_id, tag_id) 인덱스
    """

    id = fields.IntField(pk=True, generated=True)
    diary: fields.ForeignKeyRelation["Diary"] = fields.ForeignKeyField(
        "models.Diary",
        related_name="diary_tags",
        on_delete=fields.CASCADE,
        db_index=True,
    )
    tag: fields.ForeignKeyRelation["Tag"] = fields.ForeignKeyField(
        "models.Tag",
        related_name="diary_tags",
        on_delete=fields.CASCADE,
        db_index=True,
    )

    class Meta:
        table = "diary_tag"
        unique_together = (("diary", "tag"),)
        indexes = (("diary", "tag"),)

    # def __str__(self) -> str:
    #     return f"DiaryTag(diary_id={self.diary.id}, tag_id={self.tag.id})"
