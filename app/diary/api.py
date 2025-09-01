from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Annotated, List, Optional
from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

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
from app.files.service import CloudinaryService

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


def _merge_unique(a: Optional[List[str]], b: Optional[List[str]]) -> List[str]:
    out, seen = [], set()
    for src in (a or []), (b or []):
        for u in src:
            s = (u or "").strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
    return out


# ---------------------------------------------------------------------
# 다이어리 생성 API
# POST /diaries
# ---------------------------------------------------------------------
@router.post("", response_model=DiaryResponse, status_code=201)
async def create_diary(
    payload_json: Annotated[str, Form(...)],
    image_files: Annotated[Optional[List[UploadFile]], File()] = None,
):
    # 1) JSON 파싱
    try:
        payload = DiaryCreate.model_validate_json(payload_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"payload_json 파싱 실패: {e}")

    # 2) 파일 업로드 → URL
    uploaded_urls = await CloudinaryService.upload_images_to_urls(image_files)

    # 3) 업로드 URL 저장 (순서 보존/중복 제거)
    payload.image_urls = uploaded_urls

    # 4) 서비스 호출(AI는 주입되면 사용, 없으면 자동 스킵)
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
        raise HTTPException(status_code=404, detail="존재하지않는 다이어리입니다.")
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
    # Enum으로 검증 ('긍정'/'부정'/'중립' 등) — 미지정 시 None
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
    status_code=status.HTTP_200_OK,  # PATCH는 200
)
async def update_diary(
    diary_id: int,
    payload_json: Annotated[str, Form(...)],  # 필수(멀티파트 전용)
    image_files: Annotated[
        Optional[List[UploadFile]], File()
    ] = None,  # 선택(없어도 멀티파트 OK)
):
    # 1) JSON 파싱 (부분수정 스키마)
    try:
        patch = DiaryUpdate.model_validate_json(payload_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"payload_json 파싱 실패: {e}")

    # 2) 파일 업로드(있을 때만)
    uploaded = await CloudinaryService.upload_images_to_urls(image_files)

    # 3) 이미지 반영 규칙
    #    - patch.image_urls가 오면: 그 값으로 '교체'
    #    - patch.image_urls가 비었고, 업로드가 있으면: 업로드로 '교체'
    #    - 둘 다 없으면: 이미지 '유지'
    if patch.image_urls is not None:
        # 클라이언트가 명시적으로 보낸 URL로 교체(업로드 있으면 병합하고 싶으면 아래로 교체)
        patch.image_urls = (
            _merge_unique(patch.image_urls, uploaded) if uploaded else patch.image_urls
        )
    elif uploaded:
        patch.image_urls = uploaded  # 업로드만 온 경우 교체
    # else: None → 서비스에서 이미지 유지

    # 4) 서비스로 위임(보낸 필드만 부분 업데이트)
    res = await DiaryService.update(diary_id, patch)
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
    date_from: Optional[date] = Query(None, description="조회 시작일 (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="조회 종료일 (YYYY-MM-DD)"),
):
    """
    감정 통계 요약
    - Query Params: user_id, date_from, date_to
    - user_id 지정 시 해당 사용자의 통계, 미지정 시 전체 사용자 대상
    - date_from/to 지정 시 해당 기간 내 일기만 집계, 미지정 시 전체 기간
    - Response: 감정별 카운트 딕셔너리 (예: {"긍정": 3, "부정": 1, "중립": 2})
    """

    return {
        "items": await DiaryService.emotion_stats(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
    }


@router.get("/stats/daily", response_model_exclude_none=True)
async def stats_daily(
    user_id: Optional[int] = Query(None, description="특정 사용자 ID"),
    date_to: Optional[date] = Query(None, description="조회 기준일 (YYYY-MM-DD)"),
    days: int = Query(7, ge=1, le=365, description="최근 N일 (기본 7, 오늘 포함)"),
):
    """
    - date_to가 주어지면: [date_to - (days-1) ~ date_to] 범위 일간
    - date_to가 없으면: 타임존 기준 오늘을 date_to로 사용
    - user_id 미지정 시 전체 사용자 기준
    - 반환: {"period":"daily","from":YYYY-MM-DD,"to":YYYY-MM-DD,"items":[...]}
    """
    zone = ZoneInfo("Asia/Seoul")

    # 기준일 결정(없으면 타임존 기준 오늘)
    today = datetime.now(zone).date()
    to_d = date_to or today
    from_d = to_d - timedelta(days=days - 1)

    # 날짜 → [00:00, 다음날 00:00) (타임존 포함)로 변환
    dt_from = datetime.combine(from_d, time.min).replace(tzinfo=zone)
    dt_to = datetime.combine(to_d + timedelta(days=1), time.min).replace(tzinfo=zone)

    return {
        "items": await DiaryService.emotion_stats(
            user_id=user_id,
            date_from=dt_from,
            date_to=dt_to,
        )
    }
