from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime
from typing import Any, Dict, List, Mapping, Optional, Union, cast

import anyio
from fastapi import HTTPException, logger
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
from app.tag.schema import TagResponse, to_tag_response
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
        tags=[TagOut(name=t.name) for t in getattr(diary, "tags", [])],
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


# ---------------------------------------------------------------------
# 서비스 계층 (비즈니스 로직 담당)
# 컨트롤러(api.py)와 DB(repository.py) 사이에서 중간 역할
# ---------------------------------------------------------------------
class DiaryService:
    @staticmethod
    async def create(payload: DiaryCreate) -> DiaryResponse:
        """
        1) 다이어리/태그/이미지 생성(단일 트랜잭션)
        2) 커밋 후 AI 분석(있으면) → main_emotion / emotion_analysis_report 갱신
        3) 최종 1회 프리패치 조회 → DiaryResponse 반환
        """
        ai = _resolve_ai()

        # 1) 생성 + 관계 저장 (같은 커넥션으로 일관 처리)
        async with in_transaction() as conn:
            diary: Diary = await repository.create(payload, using_db=conn)
            if payload.tags:
                await repository.replace_tags(diary, payload.tags, using_db=conn)

            if payload.image_urls:
                await repository.replace_images(
                    diary, payload.image_urls, using_db=conn
                )

        # 2) 커밋 이후 AI 분석 (옵션)
        ai_result = None
        content_txt = (payload.content or "").strip()
        if content_txt and len(content_txt) < 10:
            raise HTTPException(
                status_code=422, detail="내용은 10자 초과로 작성해 주세요."
            )

        if ai and not payload.emotion_analysis_report:
            try:
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
                            "main_emotion": getattr(ai_result, "main_emotion", None),
                            "emotion_analysis_report": to_dict(ai_result),
                        },
                    )

                if scope.cancelled_caught:
                    logger.logger.warning(
                        "AI 분석 타임아웃: 감정분석 생략(생성은 유지)"
                    )
            except Exception as e:
                logger.logger.warning("AI 분석 실패(생성은 유지): %s", e)

        # 3) 최종 1회만 DB 조회(태그/이미지/유저 프리패치)
        fresh = await repository.get_by_id(diary.id)
        resp = to_diary_response(fresh)

        # 방금 AI 저장이 반영되지 않았을 가능성까지 보정
        if ai_result is not None:
            resp.main_emotion = getattr(ai_result, "main_emotion", resp.main_emotion)
            resp.emotion_analysis_report = ai_result

        return resp

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
        tag_keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[DiaryResponse], int]:
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
            tag_keyword=tag_keyword,
            page=page,
            page_size=page_size,
        )
        return [to_diary_response(r) for r in rows], total

    @staticmethod
    async def update(
        origin_diary: DiaryResponse, payload: DiaryUpdate
    ) -> Optional[DiaryResponse]:
        """
        다이어리 수정 서비스
        - 스칼라 필드만 부분 업데이트
        - tags / image_urls 는 '전체 교체' 정책
        - 최종 응답은 repository.to_response 로 일관 반환
        """
        ai = _resolve_ai()

        # 0) 대상 로드
        d = await repository.get_by_id(origin_diary.id)
        if not d:
            return None

        # 1) 스칼라 부분 업데이트 패치 구성
        patch: Dict[str, Any] = {}

        if payload.title is not None:
            patch["title"] = payload.title

        if payload.content is not None:
            # 내용이 변경되었을 때만 내용과 새 AI 분석 반영 (빈 문자열이면 초기화 처리)
            patch["content"] = payload.content

            # AI 분석 (옵션)
            ai_result = None
            if ai:
                try:
                    with anyio.move_on_after(6) as scope:
                        req = DiaryEmotionRequest(
                            diary_content=payload.content,
                            user_id=origin_diary.user_id,
                        )
                        ai_result = await ai.analyze_diary_emotion(req)
                        # DB 반영: main_emotion + emotion_analysis_report
                        await repository.update_partially(
                            d,
                            {
                                "main_emotion": getattr(
                                    ai_result, "main_emotion", None
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

        if patch:
            d = await repository.update_partially(d, patch)

        # 2) 관계 전체 교체 (None=미변경)
        if payload.tags is not None:
            await repository.replace_tags(d, payload.tags)

        if payload.image_urls is not None:
            await repository.replace_images(d, payload.image_urls)

        # 3) 응답 변환
        trans_resp = to_diary_response(d)

        # 전달된 경우에만 응답의 태그/이미지 오버라이드
        if payload.tags is not None:
            trans_resp.tags = [
                TagOut(name=(t.name if hasattr(t, "name") else str(t)).strip())
                for t in payload.tags
                if isinstance(getattr(t, "name", t), str)
                and str(getattr(t, "name", t)).strip()
            ]

        if payload.image_urls is not None:
            urls: List[str] = list(payload.image_urls)  # mypy: 확실히 List[str]로
            trans_resp.image_urls = [
                DiaryImageOut(url=u, order=i + 1) for i, u in enumerate(urls)
            ]

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

    @staticmethod
    async def get_tags_by_diary(diary_id: int) -> List[TagResponse]:
        """
        특정 일기의 태그 목록 조회 서비스
        """
        diary = await repository.get_by_id(diary_id)
        if not diary:
            return []

        # 태그 정보가 이미 prefetch되어 있어야 함
        # tags = getattr(diary, "tags", [])
        await diary.fetch_related("tags__diaries")
        tags = list(diary.tags)
        return [to_tag_response(tag) for tag in tags]

    @staticmethod
    async def search_by_tags(
        *,
        tag_names: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        main_emotion: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[DiaryResponse], int]:
        """
        태그명으로 일기 검색 서비스
        """
        rows, total = await repository.search_by_tags(
            tag_names=tag_names,
            user_id=user_id,
            main_emotion=main_emotion,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        return [to_diary_response(r) for r in rows], total

    @staticmethod
    async def add_tags_to_diary(
        diary_id: int, tag_names: List[str]
    ) -> List[TagResponse]:
        """
        특정 일기에 태그 추가 서비스
        - 기존 태그는 유지하고 새로운 태그 추가
        """
        diary = await repository.get_by_id(diary_id)
        if not diary:
            raise ValueError("일기를 찾을 수 없습니다.")

        # 기존 태그명 가져오기
        # existing_tags = getattr(diary, "tags", [])
        existing_tags = list(diary.tags)
        existing_tag_names = {tag.name for tag in existing_tags}

        # 새로운 태그명 추가 (중복 제거)
        all_tag_names = list(existing_tag_names | set(tag_names))

        # 태그 전체 교체 (기존 + 신규)
        await repository.replace_tags(diary, all_tag_names)


        # 업데이트된 태그 목록 반환
        updated_diary = await repository.get_by_id(diary_id)
        await updated_diary.fetch_related("tags", "tags__diaries")
        updated_tags = list(updated_diary.tags)

        return [to_tag_response(tag) for tag in updated_tags]

    @staticmethod
    async def remove_tags_from_diary(
        diary_id: int, tag_names: List[str]
    ) -> List[TagResponse]:
        """
        특정 일기에서 태그 제거 서비스
        """
        diary = await repository.get_by_id(diary_id)
        if not diary:
            raise ValueError("일기를 찾을 수 없습니다.")

        # 기존 태그명 가져오기
        existing_tags = getattr(diary, "tags", [])
        existing_tag_names = {getattr(tag, "name", "") for tag in existing_tags}

        # 제거할 태그명들 빼기
        remaining_tag_names = list(existing_tag_names - set(tag_names))

        # 태그 전체 교체 (제거 후 남은 것들)
        await repository.replace_tags(diary, remaining_tag_names)

        # 업데이트된 태그 목록 반환
        updated_diary = await repository.get_by_id(diary_id)
        updated_tags = getattr(updated_diary, "tags", [])
        return [to_tag_response(tag) for tag in updated_tags]

    @staticmethod
    async def get_diary_count_by_tags(tag_names: List[str]) -> dict[str, int]:
        """
        각 태그별 일기 개수 통계
        """
        stats = {}
        for tag_name in tag_names:
            count = await repository.count_diaries_by_tag_name(tag_name)
            stats[tag_name] = count
        return stats
