from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, List, Optional, Protocol

from fastapi import Form
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ai.schema import DiaryEmotionResponse
from app.diary.model import Diary, MainEmotionType

# ============================================================
# 1) 공통 유효성 타입(제약 모음)
# ============================================================
DiaryTitle = Annotated[str, Field(min_length=1, max_length=50)]
DiaryContent = Annotated[str, Field(min_length=1, max_length=5000)]

PageNum = Annotated[int, Field(ge=1)]
PageSize = Annotated[int, Field(ge=1, le=100)]


# ============================================================
# 2) 공통 서브 모델 (서브 구조, 공용으로 쓰일 수 있는 것들)
# ============================================================
class TagIn(BaseModel):
    """
    입력용 태그 스키마
    - name 필수
    """

    model_config = ConfigDict(from_attributes=True)
    name: str


class TagOut(BaseModel):
    """
    응답용 태그(단순 이름만).
    """

    model_config = ConfigDict(from_attributes=True)

    name: str


# ============================================================
# 3) 요청(Request) 스키마
#    - 생성/수정 등 클라이언트 → 서버로 들어오는 구조
#    - tags/images는 다양한 입력을 허용하고 스키마에서 정규화
# ============================================================
class DiaryBase(BaseModel):
    """
    다이어리 생성/수정 공통 필드
    """

    model_config = ConfigDict(from_attributes=True)

    title: DiaryTitle
    content: DiaryContent
    main_emotion: Optional[MainEmotionType] = Field(
        default=None, description="주요 감정. 미지정 시 null"
    )


class DiaryCreate(DiaryBase):
    """
    다이어리 생성 요청
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    emotion_analysis_report: Optional[DiaryEmotionResponse] = None
    tags: List[str] = Field(default_factory=list, description="태그 목록")
    image_urls: List[str] = Field(default_factory=list, description="이미지 URL 목록")

    @classmethod
    def as_form(
        cls,
        user_id: Annotated[int, Form(...)],
        title: Annotated[str, Form(...)],
        content: Annotated[str, Form(...)],
        tags: Annotated[Optional[List[str]], Form(None)] = None,  # tags=일상&tags=행복
        image_urls: Annotated[
            Optional[List[str]], Form(None)
        ] = None,  # URL로 주는 경우
        emotion_analysis_report: Annotated[
            Optional[str], Form(None)
        ] = None,  # JSON 문자열
    ) -> "DiaryCreate":
        return cls.model_validate(
            {
                "user_id": user_id,
                "title": title,
                "content": content,
                "tags": tags or [],
                "image_urls": image_urls or [],
                "emotion_analysis_report": (
                    json.loads(emotion_analysis_report)
                    if isinstance(emotion_analysis_report, str)
                    and emotion_analysis_report.strip()
                    else None
                ),
            }
        )


class DiaryUpdate(DiaryBase):
    """
    다이어리 부분 수정 요청
    - 모든 필드를 Optional로 선언: 전달된 값만 수정
    - tags/images는 값이 오면 '전체 교체', None이면 '변경 없음'
    - tags: 문자열/객체 혼용 허용
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    emotion_analysis_report: Optional[DiaryEmotionResponse] = None
    tags: List[str] = Field(default_factory=list, description="태그 목록")
    image_urls: List[str] = Field(default_factory=list, description="이미지 URL 목록")

    @field_validator("image_urls", mode="before")
    @classmethod
    def _coerce_images(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            raise TypeError("images는 문자열 리스트여야 합니다.")
        return [s.strip() for s in v if isinstance(s, str) and s.strip()]


# ============================================================
# 4) 응답(Response) 스키마
#    - 서버 → 클라이언트로 나가는 구조
# ============================================================
class DiaryImageOut(BaseModel):
    """
    다이어리 이미지 응답
    """

    model_config = ConfigDict(from_attributes=True)

    url: str
    order: int = 1


class DiaryResponse(DiaryBase):
    """
    단건 다이어리 조회 응답
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    emotion_analysis_report: Optional[DiaryEmotionResponse] = None
    tags: List[TagOut] = Field(default_factory=list)
    image_urls: List[DiaryImageOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DiaryListItem(BaseModel):
    """
    목록 조회용 요약 아이템
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    main_emotion: Optional[MainEmotionType] = None
    created_at: datetime


class PageMeta(BaseModel):
    """
    페이지네이션 메타 정보
    """

    model_config = ConfigDict(from_attributes=True)

    page: PageNum = 1
    page_size: PageSize = 20
    total: int = Field(0, ge=0)


class DiaryListResponse(BaseModel):
    """
    다이어리 목록 응답
    """

    model_config = ConfigDict(from_attributes=True)

    items: list[DiaryListItem]
    meta: PageMeta


# ============================================================
# 5) 매퍼 유틸 (ORM → 스키마)
#    - 서비스/레포에서 재사용할 수 있게 변환 함수
#    - ORM 객체/사전(dict) 혼용을 고려하여 안전 처리
# ============================================================


# --- 최소 접근 필드를 명시한 Protocol들 ---
class _DiaryLike(Protocol):
    """다이어리 ORM 모델이 만족해야 하는 최소 필드 집합(타입 힌트용)."""

    id: int
    user_id: int
    title: str
    content: str
    main_emotion: Optional[Any]
    created_at: Any
    updated_at: Any


# ---------- 공개 매퍼 ----------
def to_diary_list_item_from_model(diary: Diary) -> DiaryListItem:
    """
    Tortoise ORM Diary 객체 → 목록 요약 스키마(DiaryListItem) 변환
    """
    return DiaryListItem(
        id=diary.id,
        user_id=diary.user.id,
        title=diary.title,
        main_emotion=getattr(diary, "main_emotion", None),
        created_at=diary.created_at,
    )
