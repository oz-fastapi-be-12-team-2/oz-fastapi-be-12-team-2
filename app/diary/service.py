from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any, Dict, Mapping, Optional, Union

from app.ai.schema import DiaryEmotionResponse
from app.diary import repository
from app.diary.model import MainEmotionType
from app.diary.schema import (
    DiaryCreate,
    DiaryImageOut,
    DiaryResponse,
    DiaryUpdate,
    TagOut,
)

# ---------------------------------------------------------------------
# 내부 유틸 함수 (emotion_analysis 처리용)
# ---------------------------------------------------------------------


# DiaryEmotionResponse → dict 변환 (DB 저장 시 JSON으로 직렬화하기 위함)
def _ea_to_dict(ea: Optional[DiaryEmotionResponse]) -> Optional[dict]:
    if ea is None:
        return None
    return ea.model_dump()  # pydantic v1 기준


# main_emotion이 없을 때, emotion_analysis 기반으로 최종 감정을 추론하는 함수
def _infer_final_emotion(
    main_emotion: Optional[str | MainEmotionType],
    ea: Optional[Mapping[str, Any]],
) -> str:
    """
    main_emotion이 있는 diary 대상으로
    - main_emotion 우선
    - 없으면 ea["label"]
    - 그래도 없으면 positive/negative/neutral 점수 중 가장 높은 값
    - 아무 정보가 없으면 "UNSPECIFIED"
    """
    # 1) main_emotion 지정돼 있으면 그대로 반환
    if main_emotion:
        return (
            main_emotion.value
            if isinstance(main_emotion, MainEmotionType)
            else str(main_emotion)
        )

    # 2) ea가 없으면 추론 불가
    if ea is None:
        return "UNSPECIFIED"

    # 3) label 직접 지정돼 있으면 그대로 반환
    label = ea.get("label")
    if isinstance(label, str) and label:
        return label

    # 4) 점수 기반 추론
    scores: Dict[str, float] = {}
    for key in ("positive", "negative", "neutral"):
        v = ea.get(key)
        if isinstance(v, (int, float)):
            scores[key] = float(v)

    if not scores:
        return "UNSPECIFIED"

    best_key, _ = max(scores.items(), key=lambda kv: kv[1])
    return {"positive": "긍정", "negative": "부정", "neutral": "중립"}.get(
        best_key, "UNSPECIFIED"
    )


# Diary ORM 객체 → DiaryResponse(Pydantic) 변환
# 서비스/레포에서 재사용할 수 있게 변환해주는 함수
def to_diary_response(diary) -> DiaryResponse:
    """
    Tortoise ORM Diary 객체 → DiaryResponse 스키마 변환.
    (이미 prefetch_related('images','tags','user')가 되어 있다고 가정)
    """
    return DiaryResponse(
        diary_id=diary.id,
        user_id=diary.user_id,
        title=diary.title,
        content=diary.content,
        main_emotion=diary.main_emotion,
        emotion_analysis=diary.emotion_analysis,
        # tags=[TagOut(name=t.name) for t in getattr(diary, "tags", [])],
        tags=[
            TagOut(name=getattr(t, "tag_name", "")) for t in getattr(diary, "tags", [])
        ],
        images=[
            DiaryImageOut(
                url=getattr(
                    img, "url", getattr(img, "image", "")
                ),  # url or image 필드 호환
                order=img.order,
            )
            for img in getattr(diary, "images", [])
        ],
        created_at=diary.created_at,
        updated_at=diary.updated_at,
    )


# main_emotion을 문자열로 통일하는 헬퍼 (Enum/str 혼용 대비)
def _norm_emotion(e: Optional[Union[str, MainEmotionType]]) -> Optional[str]:
    if e is None:
        return None

    if isinstance(e, MainEmotionType):
        return e.value

    s = str(e).strip()
    if not s:
        raise ValueError("main_emotion은 비어 있을 수 없습니다.")

    try:
        return MainEmotionType(s).value
    except ValueError:
        allowed = ", ".join(m.value for m in MainEmotionType)
        raise ValueError(f"Invalid main_emotion: {s!r}. 허용값: [{allowed}]")


# ---------------------------------------------------------------------
# 서비스 계층 (비즈니스 로직 담당)
# 컨트롤러(api.py)와 DB(repository.py) 사이에서 중간 역할
# ---------------------------------------------------------------------


class DiaryService:
    @staticmethod
    async def create(payload: DiaryCreate) -> DiaryResponse:
        """
        다이어리 생성 서비스
        - repository.create 호출해서 DB 저장
        - DiaryEmotionResponse JSON 직렬화해서 DB 저장
        - 결과를 DiaryResponse 형태로 변환 후 반환
        """
        created = await repository.create(payload)
        return to_diary_response(created)

    @staticmethod
    async def get(diary_id: int) -> Optional[DiaryResponse]:
        """
        다이어리 단건 조회 서비스
        """
        d = await repository.get_by_id(diary_id)
        if not d:
            return None
        return to_diary_response(d)

    @staticmethod
    async def list(
        *,
        user_id: Optional[int] = None,
        main_emotion: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DiaryResponse], int]:
        """
        다이어리 목록 조회 서비스
        - 필터(user_id, main_emotion, 기간)를 적용해서 페이징 처리
        - repository.list_by_filters 호출
        """
        rows, total = await repository.list_by_filters(
            user_id=user_id,
            main_emotion=main_emotion,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        return [to_diary_response(r) for r in rows], total

    @staticmethod
    async def update(diary_id: int, payload: DiaryUpdate) -> Optional[DiaryResponse]:
        """
        다이어리 수정 서비스
        - 필요한 값만 patch dict에 담아 repository.update_partially 호출
        - tags/images는 전체 교체 정책
        """
        d = await repository.get_by_id(diary_id)
        if not d:
            return None

        patch: dict = {}
        if payload.title is not None:
            patch["title"] = payload.title
        if payload.content is not None:
            patch["content"] = payload.content
        if payload.main_emotion is not None:
            patch["main_emotion"] = (
                payload.main_emotion.value
                if isinstance(payload.main_emotion, MainEmotionType)
                else payload.main_emotion
            )
        if payload.emotion_analysis is not None:
            patch["emotion_analysis"] = _ea_to_dict(payload.emotion_analysis)

        # DB 반영
        d = await repository.update_partially(d, patch)

        # 태그/이미지 교체
        if payload.tags is not None:
            await repository.replace_tags(d, payload.tags)
        if payload.images is not None:
            await repository.replace_images(d, payload.images)

        d = await repository.get_by_id(diary_id)
        return to_diary_response(d) if d else None

    @staticmethod
    async def delete(diary_id: int) -> bool:
        """
        다이어리 삭제 서비스
        """
        d = await repository.get_by_id(diary_id)
        if not d:
            return False
        await repository.delete(d)
        return True

    @staticmethod
    async def emotion_stats(
        *,
        user_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict[str, int]:
        """
        감정 통계 서비스
        - 특정 유저/기간 조건에 맞는 다이어리를 모아 주요 감정별 개수 집계
        - main_emotion이 없을 경우 skip, 있는 경우만 통계
        """

        # 1) 조건에 맞는 다이어리 전부 조회 (사실상 전체)
        rows, _ = await repository.list_by_filters(
            user_id=user_id,
            main_emotion=None,
            date_from=date_from,
            date_to=date_to,
            page=1,
            page_size=10_000_000,
        )

        # 2) 카운터로 감정별 집계
        counter: Counter[str] = Counter()

        for r in rows:
            # main_emotion만 사용 (없으면 카운트 생략)
            label = _norm_emotion(r.main_emotion)
            if label is not None:
                counter[label] += 1

        # 5) {"긍정": 3, "부정": 1, "중립": 2, "UNSPECIFIED": 0, ...} 형태로 반환
        return dict(counter)
