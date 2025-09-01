from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class Tag(Model):
    """
    태그 모델
    - 일기와 다대다 관계
    - 태그명은 unique 제약 (같은 이름의 태그는 하나만 존재)
    - 시간 정보는 불필요 (태그는 불변의 분류 라벨)
    """

    id = fields.IntField(pk=True, generated=True)
    name = fields.CharField(max_length=50, unique=True, index=True)

    # 다대다 관계: 하나의 태그는 여러 일기에 사용될 수 있고,
    # 하나의 일기는 여러 태그를 가질 수 있음

    class Meta:
        table = "tags"
        ordering = ["name"]  # 기본 정렬: 이름순

    def __str__(self) -> str:
        return f"Tag(id={self.id}, name={self.name})"

    async def get_diary_count(self) -> int:
        """
        이 태그가 사용된 일기 수 반환
        """
        return await self.diaries.all().count()
