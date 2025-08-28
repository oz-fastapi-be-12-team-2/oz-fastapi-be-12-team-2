from __future__ import annotations

from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.diary.model import MainEmotion

# ============================================================
# 1) 공통 유효성 타입(제약 모음)
# ============================================================
DiaryTitle = Annotated[str, Field(min_length=1, max_length=50)]
DiaryContent = Annotated[str, Field(min_length=1, max_length=5000)]

# 페이지네이션 용
PageNum = Annotated[int, Field(ge=1)]
PageSize = Annotated[int, Field(ge=1, le=100)]


# ============================================================
# 2) 공통 서브 모델 (서브 구조, 공용으로 쓰일 수 있는 것들)
# ============================================================
class EmotionAnalysis(BaseModel):
    """
    감정 분석 결과를 담는 구조.
    예) {"label":"긍정","positive":0.7,"negative":0.2,"neutral":0.1}
    """

    model_config = ConfigDict(from_attributes=True)

    label: Optional[MainEmotion] = Field(
        default=None, description="모델이 예측한 대표 감정 라벨(없으면 null)"
    )
    positive: Optional[float] = Field(None, ge=0.0, le=1.0)
    negative: Optional[float] = Field(None, ge=0.0, le=1.0)
    neutral: Optional[float] = Field(None, ge=0.0, le=1.0)


# ============================================================
# 3) 요청(Request) 스키마
#    - 생성/수정 등 클라이언트 → 서버로 들어오는 구조
# ============================================================
class DiaryBase(BaseModel):
    """
    생성/수정 공통 필드
    """

    # ORM 객체를 바로 Pydantic 스키마에 넣어 직렬화할 수 있게 해주는 옵션
    # input User(1, "겨울")을 넣으면 User(id=1, name="겨울")로 변환
    model_config = ConfigDict(from_attributes=True)

    title: DiaryTitle
    content: DiaryContent
    # TODO: 감정분석 AI 결과 추후 추가 필요
    main_emotion: Optional[MainEmotion] = Field(
        default=None, description="주요 감정. 미지정 시 null"
    )


class DiaryCreate(DiaryBase):
    """
    다이어리 생성 요청
    - 태그/이미지는 문자열 배열로 받는다
      (서비스 레이어에서 Tag upsert, Image row 생성)
    """

    user_id: int
    emotion_analysis: Optional[EmotionAnalysis] = None
    tags: List[str] = Field(default_factory=list, description="태그 문자열 목록")
    images: List[str] = Field(default_factory=list, description="이미지 URL 목록")


class DiaryUpdate(BaseModel):
    """
    다이어리 부분 수정 요청
    - 모든 필드를 Optional로 선언: 전달된 값만 수정
    - tags/images는 값이 오면 '전체 교체', None이면 '변경 없음'
    """

    model_config = ConfigDict(from_attributes=True)

    title: Optional[DiaryTitle] = None
    content: Optional[DiaryContent] = None
    main_emotion: Optional[MainEmotion] = None
    emotion_analysis: Optional[EmotionAnalysis] = None
    tags: Optional[List[str]] = None
    images: Optional[List[str]] = None


# ============================================================


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


class TagOut(BaseModel):
    """
    태그 응답 (단순 이름만)
    """

    model_config = ConfigDict(from_attributes=True)

    name: str


class DiaryResponse(DiaryBase):
    """
    단건 다이어리 조회 응답
    """

    model_config = ConfigDict(from_attributes=True)

    diary_id: int
    user_id: int
    emotion_analysis: Optional[EmotionAnalysis] = None
    tags: List[TagOut] = Field(default_factory=list)
    images: List[DiaryImageOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DiaryListItem(BaseModel):
    """
    목록 조회용 요약 아이템
    """

    model_config = ConfigDict(from_attributes=True)

    diary_id: int
    user_id: int
    title: str
    main_emotion: Optional[MainEmotion] = None
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

    items: List[DiaryListItem]
    meta: PageMeta
