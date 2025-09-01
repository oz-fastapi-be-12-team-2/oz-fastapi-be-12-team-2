from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.diary.model import MainEmotionType
from app.diary.schema import (
    DiaryCreate,
    DiaryListItem,
    DiaryListResponse,
    DiaryResponse,
    DiaryUpdate,
    PageMeta,
)
from app.diary.service import DiaryService

# ---------------------------------------------------------------------
# 다이어리 API 라우터
# - prefix="/diaries"  → 모든 경로가 /diaries/... 로 시작
# - tags=["Diaries"]   → Swagger UI에서 다이어리 그룹으로 묶임
# - default_response_class 등은 필요 시 추가 설정
# ---------------------------------------------------------------------
router = APIRouter(prefix="/diaries", tags=["Diaries"])


# ---------------------------------------------------------------------
# 내부 헬퍼: 다양한 형태를 DiaryListItem으로 안전 변환
# - Service가 ORM 객체 / DiaryResponse / DiaryListItem 을 반환해도 대응
# ---------------------------------------------------------------------
def _as_list_item(x: object) -> DiaryListItem:
    """
    입력 x 를 DiaryListItem으로 변환.
    우선순위:
      1) 이미 DiaryListItem 이면 그대로
      2) DiaryResponse 이면 주요 필드만 추려서 요약으로 변환
      3) ORM-like 객체면 속성 접근으로 변환 (id/user_id/title/main_emotion/created_at)
    """
    if isinstance(x, DiaryListItem):
        return x

    if isinstance(x, DiaryResponse):
        return DiaryListItem(
            id=x.id,
            user_id=x.user_id,
            title=x.title,
            main_emotion=x.main_emotion,
            created_at=x.created_at,
        )

    # ORM-like: duck typing
    return DiaryListItem(
        id=getattr(x, "id"),
        user_id=getattr(x, "user_id"),
        title=getattr(x, "title"),
        main_emotion=getattr(x, "main_emotion", None),
        created_at=getattr(x, "created_at"),
    )


# ---------------------------------------------------------------------
# 다이어리 생성 API
# POST /diaries
# ---------------------------------------------------------------------
@router.post(
    "",
    response_model=DiaryResponse,
    status_code=201,
    # response_model_exclude_none=True,
)
async def create_diary(payload: DiaryCreate):
    """
    다이어리 생성
    - Request Body: DiaryCreate (title, content, user_id, tags, images 등)
    - Response: 생성된 다이어리 전체 정보 (DiaryResponse)
    """
    return await DiaryService.create(payload)


# ---------------------------------------------------------------------
# 다이어리 단건 조회 API
# GET /diaries/{diary_id}
# ---------------------------------------------------------------------
@router.get(
    "/{diary_id}",
    response_model=DiaryResponse,
    response_model_exclude_none=True,
)
async def get_diary(diary_id: int):
    """
    다이어리 단건 조회
    - Path Param: diary_id (조회할 다이어리 ID)
    - Response: DiaryResponse
    """
    res = await DiaryService.get(diary_id)
    if not res:
        raise HTTPException(status_code=404, detail="Diary not found")
    return res


# ---------------------------------------------------------------------
# 다이어리 목록 조회 API (페이징)
# GET /diaries
# ---------------------------------------------------------------------
@router.get(
    "",
    response_model=DiaryListResponse,
    response_model_exclude_none=True,
)
async def list_diaries(
    user_id: Optional[int] = Query(None, description="특정 사용자 ID로 필터링"),
    # ✅ Enum으로 검증 ('긍정'/'부정'/'중립' 등) — 미지정 시 None
    main_emotion: Optional[MainEmotionType] = Query(
        None, description="주요 감정 라벨로 필터링"
    ),
    date_from: Optional[datetime] = Query(None, description="조회 시작일 (YYYY-MM-DD)"),
    date_to: Optional[datetime] = Query(None, description="조회 종료일 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="페이지 번호(1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수(최대 100)"),
):
    """
    다이어리 목록 조회 (페이징)
    - Query Params: user_id, main_emotion, date_from, date_to, page, page_size
    - Response: DiaryListResponse (items[list[DiaryListItem]] + meta)
    """
    # Service 결과는 구현에 따라 ORM / DiaryResponse / DiaryListItem 등일 수 있음
    raw_items, total = await DiaryService.list(
        user_id=user_id,
        main_emotion=(
            main_emotion.value
            if isinstance(main_emotion, MainEmotionType)
            else main_emotion
        ),
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

    # ✅ 어떤 타입이 오든 리스트 요약으로 변환하여 mypy 에러 제거
    items: list[DiaryListItem] = [_as_list_item(it) for it in (raw_items or [])]

    return DiaryListResponse(
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


# ---------------------------------------------------------------------
# 다이어리 수정 API
# PATCH /diaries/{diary_id}
# ---------------------------------------------------------------------
@router.patch(
    "/{diary_id}",
    response_model=DiaryResponse,
    response_model_exclude_none=True,
)
async def update_diary(diary_id: int, payload: DiaryUpdate):
    """
    다이어리 수정 (부분 수정 가능)
    - Path Param: diary_id (수정할 다이어리 ID)
    - Request Body: DiaryUpdate (title, content, main_emotion 등 일부만 보내도 됨)
    - Response: 수정된 DiaryResponse
    """
    res = await DiaryService.update(diary_id, payload)
    if not res:
        raise HTTPException(status_code=404, detail="Diary not found")
    return res


# ---------------------------------------------------------------------
# 다이어리 삭제 API
# DELETE /diaries/{diary_id}
# ---------------------------------------------------------------------
@router.delete("/{diary_id}", status_code=204)
async def delete_diary(diary_id: int):
    """
    다이어리 삭제
    - Path Param: diary_id (삭제할 다이어리 ID)
    - Response: 없음 (204 No Content)
    """
    ok = await DiaryService.delete(diary_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Diary not found")
    # FastAPI는 204에서 본문을 무시하므로 명시적으로 None 반환
    return None


# ---------------------------------------------------------------------
# 감정 통계 API
# GET /diaries/stats/summary
# ---------------------------------------------------------------------
@router.get("/stats/summary", response_model_exclude_none=True)
async def stats_summary(
    user_id: Optional[int] = Query(None, description="특정 사용자 ID"),
    date_from: Optional[datetime] = Query(None, description="조회 시작일"),
    date_to: Optional[datetime] = Query(None, description="조회 종료일"),
    inferred: bool = Query(
        True, description="True: main_emotion 미지정 시 emotion_analysis로 추론"
    ),
):
    """
    감정 통계 요약
    - Query Params: user_id, date_from, date_to, inferred
    - Response: 감정별 카운트 딕셔너리 (예: {"긍정": 3, "부정": 1, "중립": 2})
    """
    return {
        "items": await DiaryService.emotion_stats(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
    }
