from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime
from typing import Any, Dict, Mapping, Optional, Union, cast

import anyio
from fastapi import logger
from pydantic import BaseModel
from tortoise.transactions import in_transaction

from app.ai.schema import DiaryEmotionRequest
from app.ai.service import DiaryEmotionService
from app.diary import repository
from app.diary.model import Diary, MainEmotionType
from app.diary.schema import (
    DiaryCreate,
    DiaryImageOut,
    DiaryResponse,
    DiaryUpdate,
    TagOut,
)
from core.config import AI_ENABLED

# ------------------------------------------------------------
# 공용 유틸
# ------------------------------------------------------------


def to_dict(
    obj: Optional[Union[BaseModel, Mapping[str, Any]]],
    *,
    exclude_none: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Pydantic / Mapping → dict 변환
    - BaseModel → model_dump(mode='json')
    - Mapping   → dict(...) (exclude_none=True면 None 제거)
    - None      → None
    """
    if obj is None:
        return None
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json", exclude_none=exclude_none)
    if isinstance(obj, Mapping):
        return {k: v for k, v in obj.items() if (v is not None or not exclude_none)}
    raise TypeError(f"to_dict 변환 불가: {type(obj)!r}")


# Diary ORM 객체 → DiaryResponse(Pydantic) 변환
# 서비스/레포에서 재사용할 수 있게 변환해주는 함수
def to_diary_response(diary) -> DiaryResponse:
    """
    Tortoise ORM Diary 객체 → DiaryResponse 스키마 변환.
    (이미 prefetch_related('images','tags','user')가 되어 있다고 가정)
    """
    return DiaryResponse(
        id=diary.id,
        user_id=diary.user_id,
        title=diary.title,
        content=diary.content,
        emotion_analysis_report=diary.emotion_analysis_report,
        tags=[TagOut(name=getattr(t, "name", "")) for t in getattr(diary, "tags", [])],
        image_urls=[
            DiaryImageOut(
                url=getattr(
                    img, "url", getattr(img, "image_urls", "")
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
        raise ValueError(f"허용하지 않는 emotion 값입니다: {s!r}. 허용값: [{allowed}]")


def _resolve_ai() -> Optional[DiaryEmotionService]:
    """
    AI 사용 가능 여부 확인 후 인스턴스 생성
    - 키 미설정/초기화 실패 시 None 반환 → 서비스에서 자동 스킵
    """
    if not AI_ENABLED:
        return None
    try:
        return DiaryEmotionService()
    except Exception:
        return None


def _extract_main_emotion_from_report(rep_obj: Any) -> Optional[str]:
    """
    다양한 형태의 emotion_analysis_report에서 main_emotion만 안전하게 추출
    - str(JSON), dict, BaseModel, None 모두 처리
    """
    if rep_obj is None:
        rep_dict: Dict[str, Any] = {}
    elif isinstance(rep_obj, str):
        try:
            parsed = json.loads(rep_obj)
            rep_dict = parsed if isinstance(parsed, dict) else {}
        except Exception:
            rep_dict = {}
    elif hasattr(rep_obj, "model_dump"):
        rep_dict = cast(Dict[str, Any], rep_obj.model_dump())
    elif isinstance(rep_obj, dict):
        rep_dict = cast(Dict[str, Any], rep_obj)
    else:
        rep_dict = {}

    ea: Any = rep_dict.get("emotion_analysis")
    if isinstance(ea, dict):
        me = ea.get("main_emotion")
    return _norm_emotion(me)


# ---------------------------------------------------------------------
# 서비스 계층 (비즈니스 로직 담당)
# 컨트롤러(api.py)와 DB(repository.py) 사이에서 중간 역할
# ---------------------------------------------------------------------
class DiaryService:
    @staticmethod
    async def create(
        payload: DiaryCreate,
    ) -> DiaryResponse:
        """
        1) 다이어리 생성(트랜잭션)
        2) 태그/이미지 전체 교체 저장
        3) 커밋 이후 AI 분석(가능하면) → main_emotion / emotion_analysis_report DB 반영
        4) 최종 DiaryResponse 반환(태그/이미지/감정 포함)
        """
        ai = _resolve_ai()

        # 1) 생성 + 관계 저장
        async with in_transaction():
            diary: Diary = await repository.create(payload)

            if payload.tags:
                # 레포지토리 시그니처에 맞춰 전달 (TagIn 리스트 or 이름 리스트)
                await repository.replace_tags(diary, payload.tags)

            if payload.image_urls:
                await repository.replace_images(diary, payload.image_urls)

        # 3) 커밋 이후 AI 분석
        ai_result = None
        # 2) 커밋 이후 AI 분석(선택)
        if ai and not payload.emotion_analysis_report:
            try:
                # 타임아웃: 지연되면 감정분석만 생략하고 생성은 유지
                with anyio.move_on_after(6) as scope:
                    req = DiaryEmotionRequest(
                        diary_content=payload.content,
                        user_id=payload.user_id,
                    )
                    ai_result = await ai.analyze_diary_emotion(req)

                    # DB 반영: main_emotion + emotion_analysis_report
                    await repository.update_partially(
                        diary,
                        {
                            "main_emotion": _norm_emotion(
                                getattr(ai_result, "main_emotion", None)
                            ),
                            "emotion_analysis_report": to_dict(ai_result),
                        },
                    )

                if scope.cancelled_caught:
                    logger.logger.warning(
                        "AI 분석 타임아웃: 감정분석 생략(생성은 유지)"
                    )
            except Exception as e:
                logger.logger.warning("AI 분석 실패(생성은 유지): %s", e)

        resp = await repository.get_by_id(diary.id)
        trans_resp = to_diary_response(resp)
        trans_resp.tags = [
            TagOut(name=(t.name if hasattr(t, "name") else str(t)).strip())
            for t in (payload.tags or [])
            if isinstance(getattr(t, "name", t), str)
            and str(getattr(t, "name", t)).strip()
        ]
        trans_resp.image_urls = [
            DiaryImageOut(url=u, order=i + 1) for i, u in enumerate(payload.image_urls)
        ]
        if ai_result is not None:
            trans_resp.emotion_analysis_report = ai_result

        return trans_resp

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
        - 스칼라 필드만 부분 업데이트
        - tags / image_urls 는 '전체 교체' 정책
        - 최종 응답은 repository.to_response 로 일관 반환
        """
        d = await repository.get_by_id(diary_id)
        if not d:
            return None

        # 1) 스칼라 부분 업데이트 패치 구성
        patch: Dict[str, Any] = {}
        if payload.title is not None:
            patch["title"] = payload.title
        if payload.content is not None:
            patch["content"] = payload.content

        if payload.emotion_analysis_report is not None:
            ea = payload.emotion_analysis_report
            if hasattr(ea, "model_dump"):
                patch["emotion_analysis_report"] = ea.model_dump()
            elif isinstance(ea, dict):
                patch["emotion_analysis_report"] = ea
            else:
                patch["emotion_analysis_report"] = (
                    ea  # str/기타도 JSONField가 수용하면 그대로
                )

        if patch:
            d = await repository.update_partially(d, patch)
        # 2) 관계 전체 교체
        if payload.tags is not None:
            await repository.replace_tags(d, payload.tags)

        if payload.image_urls is not None:
            await repository.replace_images(d, payload.image_urls)
        trans_resp = to_diary_response(d)
        trans_resp.tags = [
            TagOut(name=(t.name if hasattr(t, "name") else str(t)).strip())
            for t in (payload.tags or [])
            if isinstance(getattr(t, "name", t), str)
            and str(getattr(t, "name", t)).strip()
        ]
        trans_resp.image_urls = [
            DiaryImageOut(url=u, order=i + 1) for i, u in enumerate(payload.image_urls)
        ]
        print("service.payload", payload)
        print("service.d", trans_resp)
        # 3) 최종 응답(태그/이미지/감정 포함)
        return trans_resp

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
            rep_obj: Any = getattr(r, "emotion_analysis_report", None)

            if rep_obj is None:
                rep_dict: Dict[str, Any] = {}
            elif isinstance(rep_obj, str):
                try:
                    parsed = json.loads(rep_obj)
                    rep_dict = parsed if isinstance(parsed, dict) else {}
                except Exception:
                    rep_dict = {}
            elif hasattr(rep_obj, "model_dump"):
                rep_dict = cast(Dict[str, Any], rep_obj.model_dump())
            elif isinstance(rep_obj, dict):
                rep_dict = rep_obj
            else:
                rep_dict = {}

            me: Any = rep_dict.get("main_emotion")
            if me is None:
                ea = rep_dict.get("emotion_analysis")
                if isinstance(ea, dict):
                    me = ea.get("main_emotion")

            label = _norm_emotion(me)
            if label:
                counter[label] += 1

        # 5) {"긍정": 3, "부정": 1, "중립": 2, "UNSPECIFIED": 0, ...} 형태로 반환
        return dict(counter)
