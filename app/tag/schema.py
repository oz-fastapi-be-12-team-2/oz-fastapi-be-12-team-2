from __future__ import annotations

from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.diary.schema import DiaryListItem, PageMeta

# ============================================================
# 1) 공통 유효성 타입(제약 모음)
# ============================================================
TagName = Annotated[str, Field(min_length=1, max_length=50)]


# ============================================================
# 2) 요청(Request) 스키마
# ============================================================
class TagCreate(BaseModel):
    """
    태그 생성 요청
    """

    model_config = ConfigDict(from_attributes=True)

    name: TagName


class TagUpdate(BaseModel):
    """
    태그 수정 요청
    """

    model_config = ConfigDict(from_attributes=True)

    name: TagName


# ============================================================
# 3) 응답(Response) 스키마
# ============================================================
class TagResponse(BaseModel):
    """
    태그 응답
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    diary_count: Optional[int] = Field(
        default=None,
        description="이 태그를 사용하는 일기 수 (관련 데이터가 로드된 경우에만 제공)",
    )


class TagListResponse(BaseModel):
    """
    태그 목록 응답
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[TagResponse]
    meta: PageMeta


class TagDiaryListResponse(BaseModel):
    """
    특정 태그의 일기 목록 응답
    """

    model_config = ConfigDict(from_attributes=True)

    tag: TagResponse
    diaries: List[DiaryListItem]
    meta: PageMeta


# ============================================================
# 4) 매퍼 유틸 (ORM → 스키마)
# ============================================================
def to_tag_response(tag) -> TagResponse:
    """
    ORM Tag 객체 → TagResponse 변환
    diary_count는 prefetch_related('diaries')가 호출된 경우에만 정확한 값 제공
    """
    diary_count = None

    # diaries 관계가 prefetch되었는지 확인
    if hasattr(tag, "diaries"):
        diaries = getattr(tag, "diaries", None)
        if diaries is not None:
            try:
                # Tortoise ORM의 경우 이미 로드된 관계는 리스트처럼 동작
                if hasattr(diaries, "__len__"):
                    diary_count = len(diaries)
                elif hasattr(diaries, "count"):
                    # 만약 아직 로드되지 않았다면 None 유지 (별도 쿼리 방지)
                    pass
            except (TypeError, AttributeError) as e:
                # TypeError: len()이나 hasattr 호출 시 타입 오류
                # AttributeError: 예상하지 못한 속성 접근 오류
                diary_count = None

    return TagResponse(
        id=tag.id,
        name=tag.name,
        diary_count=diary_count,
    )
