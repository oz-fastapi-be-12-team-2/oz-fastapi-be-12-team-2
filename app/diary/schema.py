from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ai.schema import MainEmotionType

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
class EmotionAnalysis(BaseModel):
    """
    감정 분석 결과 구조.
    예) {"label": "긍정", "positive": 0.7, "negative": 0.2, "neutral": 0.1}
    """

    model_config = ConfigDict(from_attributes=True)

    label: Optional[MainEmotionType] = Field(
        default=None, description="모델이 예측한 대표 감정 라벨(없으면 null)"
    )
    positive: Optional[float] = Field(None, ge=0.0, le=1.0)
    negative: Optional[float] = Field(None, ge=0.0, le=1.0)
    neutral: Optional[float] = Field(None, ge=0.0, le=1.0)


class TagIn(BaseModel):
    """
    입력용 태그 스키마.
    - id는 선택(업서트/매핑에 사용 가능)
    - name은 필수
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
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
    - tags: ["일상","행복"] 또는 [{"name":"일상"},{"id":3,"name":"행복"}] 모두 허용
    - images: 문자열/리스트 모두 허용, 공백/빈값 제거
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    emotion_analysis: Optional[EmotionAnalysis] = None
    tags: list[TagIn] = Field(default_factory=list, description="태그 목록")
    images: list[str] = Field(default_factory=list, description="이미지 URL 목록")

    # ---- 정규화 밸리데이터: tags ----
    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, v: Any) -> Any:
        """
        허용 인풋:
          - None                         -> []
          - "일상"                       -> [{"name":"일상"}]
          - ["일상","행복"]              -> [{"name":"일상"},{"name":"행복"}]
          - [{"name":"일상"},{"id":3,"name":"행복"}] -> 그대로
          - 혼합 리스트도 허용
        """
        if v is None:
            return []
        if isinstance(v, str):
            return [{"name": v}]
        if isinstance(v, list):
            out: list[dict] = []
            for item in v:
                if isinstance(item, str):
                    out.append({"name": item})
                elif isinstance(item, dict):
                    out.append(item)  # name 유효성은 TagIn에서 검증
                else:
                    raise TypeError("tags 항목은 문자열 또는 객체여야 합니다.")
            return out
        raise TypeError("tags는 리스트 또는 문자열이어야 합니다.")

    # ---- 정규화 밸리데이터: images ----
    @field_validator("images", mode="before")
    @classmethod
    def _coerce_images(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            raise TypeError("images는 문자열 리스트여야 합니다.")
        # 공백/빈값 제거
        return [s.strip() for s in v if isinstance(s, str) and s.strip()]


class DiaryUpdate(BaseModel):
    """
    다이어리 부분 수정 요청
    - 모든 필드를 Optional로 선언: 전달된 값만 수정
    - tags/images는 값이 오면 '전체 교체', None이면 '변경 없음'
    - tags: 문자열/객체 혼용 허용
    """

    model_config = ConfigDict(from_attributes=True)

    title: Optional[DiaryTitle] = None
    content: Optional[DiaryContent] = None
    main_emotion: Optional[MainEmotionType] = None
    emotion_analysis: Optional[EmotionAnalysis] = None
    tags: Optional[list[TagIn]] = None
    images: Optional[list[str]] = None

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str):
            return [{"name": v}]
        if isinstance(v, list):
            out: list[dict] = []
            for item in v:
                if isinstance(item, str):
                    out.append({"name": item})
                elif isinstance(item, dict):
                    out.append(item)
                else:
                    raise TypeError("tags 항목은 문자열 또는 객체여야 합니다.")
            return out
        raise TypeError("tags는 리스트 또는 문자열이어야 합니다.")

    @field_validator("images", mode="before")
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

    diary_id: int
    user_id: int
    emotion_analysis: Optional[EmotionAnalysis] = None
    tags: list[TagOut] = Field(default_factory=list)
    images: list[DiaryImageOut] = Field(default_factory=list)
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


# ---------- 내부 헬퍼 ----------
def _safe_ea_to_model(ea: Any) -> Optional[EmotionAnalysis]:
    """
    emotion_analysis를 EmotionAnalysis 모델로 '안전하게' 변환.
    - None → None
    - str(JSON) → dict 로드 후 모델 검증
    - dict → 모델 검증
    - 이미 모델이면 그대로
    - 그 외 → None
    """
    if ea is None:
        return None

    if isinstance(ea, EmotionAnalysis):
        return ea

    if isinstance(ea, str):
        try:
            loaded = json.loads(ea)
        except Exception:
            return None
        if not isinstance(loaded, dict):
            return None
        try:
            return EmotionAnalysis.model_validate(loaded)
        except Exception:
            return None

    if isinstance(ea, dict):
        try:
            return EmotionAnalysis.model_validate(ea)
        except Exception:
            return None

    return None


def _tag_name(tag: Any) -> str:
    """
    Tag 모델 호환:
    - 우선 .name 사용
    - 없으면 .tag_name 사용
    - dict로 들어와도 안전 처리
    - 둘 다 없으면 빈 문자열
    """
    if isinstance(tag, dict):
        name = tag.get("name") or tag.get("tag_name")
        return name if isinstance(name, str) else ""
    name = getattr(tag, "name", None)
    if isinstance(name, str) and name:
        return name
    tag_name = getattr(tag, "tag_name", None)
    return tag_name if isinstance(tag_name, str) else ""


def _image_url(img: Any) -> str:
    """
    Image 모델 호환:
    - 우선 .url 사용
    - 없으면 .image 사용
    - dict로 들어와도 안전 처리
    """
    if isinstance(img, dict):
        url = img.get("url") or img.get("image")
        return url if isinstance(url, str) else ""
    url = getattr(img, "url", None)
    if isinstance(url, str) and url:
        return url
    image = getattr(img, "image", None)
    return image if isinstance(image, str) else ""


def _image_order(img: Any) -> int:
    """
    이미지 정렬 순서 추출 (없으면 1)
    - dict/객체 모두 호환
    """
    if isinstance(img, dict):
        order = img.get("order", 1)
        return int(order) if isinstance(order, int) else 1
    return int(getattr(img, "order", 1))


# ---------- 공개 매퍼 ----------
def to_diary_response_from_model(diary: _DiaryLike) -> DiaryResponse:
    """
    Tortoise ORM Diary 객체 → DiaryResponse 스키마 변환
    (이미 prefetch_related('images','tags','user') 되어 있다고 가정)
    - N+1 최소화: 서비스/레포 계층에서 prefetch 권장
    """
    _tags = getattr(diary, "tags", []) or []
    _images = getattr(diary, "images", []) or []

    return DiaryResponse(
        diary_id=diary.id,
        user_id=diary.user_id,
        title=diary.title,
        content=diary.content,
        main_emotion=getattr(diary, "main_emotion", None),
        emotion_analysis=_safe_ea_to_model(getattr(diary, "emotion_analysis", None)),
        tags=[TagOut(name=_tag_name(t)) for t in _tags],
        images=[
            DiaryImageOut(url=_image_url(img), order=_image_order(img))
            for img in _images
        ],
        created_at=diary.created_at,
        updated_at=diary.updated_at,
    )


def to_diary_list_item_from_model(diary: _DiaryLike) -> DiaryListItem:
    """
    Tortoise ORM Diary 객체 → 목록 요약 스키마(DiaryListItem) 변환
    """
    return DiaryListItem(
        diary_id=diary.id,
        user_id=diary.user_id,
        title=diary.title,
        main_emotion=getattr(diary, "main_emotion", None),
        created_at=diary.created_at,
    )
