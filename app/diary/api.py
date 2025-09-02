from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Optional, cast
from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
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
from app.tag.schema import TagListResponse
from app.user.auth import get_current_user
from app.user.model import User, UserRole

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

    return DiaryListItem(
        id=getattr(x, "id"),
        user_id=getattr(x, "user_id"),
        title=getattr(x, "title"),
        main_emotion=getattr(x, "main_emotion", None),
        created_at=getattr(x, "created_at"),
    )


# ---------------------------------------------------------------------
# 권한 결정
# ---------------------------------------------------------------------
# 다이어리 리스트 조회 권한 설정
def resolve_list_scope_or_raise(
    *,
    role: UserRole,
    current_user_id: int,
    user_id_param: Optional[int],
) -> Optional[int]:
    """다이어리 '목록' 조회 시 effective_user_id를 결정. 불가하면 403."""
    if user_id_param is not None:
        if role == UserRole.USER:
            if user_id_param != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{role} 권한은 본인 다이어리만 조회할 수 있습니다.",
                )
            return current_user_id
        elif role in (UserRole.STAFF, UserRole.SUPERUSER):
            return user_id_param
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다."
            )
    # user_id_param is None
    if role == UserRole.SUPERUSER:
        return None  # 전체 조회 허용
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"{role} 권한에서는 'user_id' 없이 조회할 수 없습니다. 예: /diaries?user_id=123",
    )


# 다이어리 단건 조회 권한 설정
def ensure_can_read_diary_or_raise(
    *, role: UserRole, current_user_id: int, diary_owner_id: int
) -> None:
    if role == UserRole.USER and current_user_id != diary_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{role} 권한은 본인 다이어리만 조회할 수 있습니다.",
        )


# 다이어리 수정, 삭제 권한 설정
def ensure_can_modify_diary_or_raise(
    *, current_user_id: int, diary_owner_id: int
) -> None:
    if current_user_id != diary_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인 다이어리만 수정/삭제할 수 있습니다.",
        )


# ---------------------------------------------------------------------
# 다이어리 생성 API
# POST /diaries
# ---------------------------------------------------------------------
@router.post("", response_model=DiaryResponse, status_code=201)
async def create_diary(
    title: str = Form(...),
    content: str = Form(...),
    tags: Optional[List[str]] = Form(None),  # Form으로 받아야 multipart 노출됨
    images: Optional[List[UploadFile]] = File(None),
    current_user: User = Depends(get_current_user),
):

    image_urls = await CloudinaryService.upload_images_to_urls(images)

    payload = DiaryCreate(
        user_id=current_user.id,
        emotion_analysis_report=None,
        title=title,
        content=content,
        tags=tags or [],
        image_urls=image_urls,
    )

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
async def get_diary(diary_id: int, current_user: User = Depends(get_current_user)):
    """
    다이어리 단건 조회
    - Path Param: diary_id (조회할 다이어리 ID)
    - Response: DiaryResponse
    """
    res = await DiaryService.get(diary_id)
    if not res:
        raise HTTPException(status_code=404, detail="Diary not found")
    owner_id_opt: Optional[int] = getattr(res, "user_id", None)
    owner_id = cast(int, owner_id_opt)
    ensure_can_read_diary_or_raise(
        role=current_user.user_roles,
        current_user_id=current_user.id,
        diary_owner_id=owner_id,
    )

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
    main_emotion: Optional[MainEmotionType] = Query(
        None, description="주요 감정 라벨로 필터링"
    ),
    date_from: Optional[datetime] = Query(None, description="조회 시작일 (YYYY-MM-DD)"),
    date_to: Optional[datetime] = Query(None, description="조회 종료일 (YYYY-MM-DD)"),
    tag_keyword: Optional[str] = Query(None, description="태그 검색어"),
    page: int = Query(1, ge=1, description="페이지 번호(1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수(최대 100)"),
    current_user: User = Depends(get_current_user),
):
    """
    다이어리 목록 조회 (페이징)
    - Query Params: user_id, main_emotion, date_from, date_to, page, page_size
    - user_id가 있으면:
        USER: 본인 ID와 일치할 때만 허용
        STAFF: 허용(특정 사용자 조회)
        SUPERUSER: 허용
    - user_id가 없으면:
        USER/STAFF: 불가
        SUPERUSER: 전체 조회 허용
    """
    # 1) 권한별 user scope 결정
    role = current_user.user_roles
    effective_user_id = resolve_list_scope_or_raise(
        role=role,
        current_user_id=current_user.id,
        user_id_param=user_id,
    )

    raw_items, total = await DiaryService.list(
        user_id=effective_user_id,
        main_emotion=(
            main_emotion.value
            if isinstance(main_emotion, MainEmotionType)
            else main_emotion
        ),
        tag_keyword=tag_keyword,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

    # 어떤 타입이 오든 리스트 요약으로 변환하여 mypy 에러 제거
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
async def update_diary(
    diary_id: int,
    request: Request,  # ← 원시 폼 접근용
    title: str = Form(...),
    content: str = Form(...),
    tags: Optional[List[str]] = Form(None),  # None=미변경, []=초기화, ['a','b']=교체
    current_user: User = Depends(get_current_user),
):
    # 1) 소유자 확인
    cur = await DiaryService.get(diary_id)
    if not cur:
        raise HTTPException(status_code=404, detail="Diary not found")
    owner_id = getattr(cur, "user_id", None)
    if owner_id is None:
        raise HTTPException(status_code=500, detail="일기 데이터에 user_id가 없습니다.")
    ensure_can_modify_diary_or_raise(
        current_user_id=current_user.id, diary_owner_id=owner_id
    )

    # 2) 원시 폼에서 images 직접 파싱 (문자열/빈 값은 무시)
    form = await request.form()
    raw_images = (
        form.getlist("images") if "images" in form else []
    )  # List[UploadFile | str | ...]
    valid_files: List[UploadFile] = []
    for x in raw_images:
        if isinstance(x, UploadFile) and x.filename:
            valid_files.append(x)

    image_urls: Optional[List[str]] = None  # 기본: 미변경
    if valid_files:
        image_urls = await CloudinaryService.upload_images_to_urls(valid_files)

    # 3) 태그 정리
    tags_payload: Optional[List[str]]
    if tags is None or tags == [""]:
        tags_payload = None
    else:
        tags_payload = [t.strip() for t in tags if t and t.strip()]  # []면 전체 제거

    # 4) 업데이트 페이로드
    payload = DiaryUpdate(
        title=title,
        content=content,
        image_urls=image_urls,  # None=미변경, [..]=교체
        tags=tags_payload,  # None=미변경, []=초기화
    )

    # 5) 업데이트 실행
    res = await DiaryService.update(cur, payload)
    return res


# ---------------------------------------------------------------------
# 다이어리 삭제 API
# DELETE /diaries/{diary_id}
# ---------------------------------------------------------------------
@router.delete("/{diary_id}", status_code=204)
async def delete_diary(diary_id: int, current_user: User = Depends(get_current_user)):
    """
    다이어리 삭제
    - Path Param: diary_id (삭제할 다이어리 ID)
    - Response: 없음 (204 No Content)
    """
    cur = await DiaryService.get(diary_id)
    if not cur:
        raise HTTPException(status_code=404, detail="Diary not found")

    diary_owner_id = getattr(cur, "user_id", None)
    owner_id = cast(int, diary_owner_id)

    ensure_can_modify_diary_or_raise(
        current_user_id=current_user.id, diary_owner_id=owner_id
    )

    ok = await DiaryService.delete(diary_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Diary not found")
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
    current_user: User = Depends(get_current_user),
):
    """
    감정 통계 요약
    - Query Params: user_id, date_from, date_to, inferred
    - Response: 감정별 카운트 딕셔너리 (예: {"긍정": 3, "부정": 1, "중립": 2})
    """
    # 1) 권한별 user scope 결정
    role = current_user.user_roles
    effective_user_id = resolve_list_scope_or_raise(
        role=role,
        current_user_id=current_user.id,
        user_id_param=user_id,
    )

    return {
        "items": await DiaryService.emotion_stats(
            user_id=effective_user_id,
            date_from=date_from,
            date_to=date_to,
        )
    }


@router.get("/stats/daily", response_model_exclude_none=True)
async def stats_daily(
    user_id: Optional[int] = Query(None, description="특정 사용자 ID"),
    date_to: Optional[date] = Query(None, description="조회 기준일 (YYYY-MM-DD)"),
    days: int = Query(7, ge=1, le=365, description="최근 N일 (기본 7, 오늘 포함)"),
    current_user: User = Depends(get_current_user),
):
    """
    - date_to가 주어지면: [date_to - (days-1) ~ date_to] 범위 일간
    - date_to가 없으면: 타임존 기준 오늘을 date_to로 사용
    - user_id 미지정 시 전체 사용자 기준
    - 반환: {"period":"daily","from":YYYY-MM-DD,"to":YYYY-MM-DD,"items":[...]}
    """
    zone = ZoneInfo("Asia/Seoul")

    # 1) 권한별 user scope 결정
    role = current_user.user_roles
    effective_user_id = resolve_list_scope_or_raise(
        role=role,
        current_user_id=current_user.id,
        user_id_param=user_id,
    )

    # 기준일 결정(없으면 타임존 기준 오늘)
    today = datetime.now(zone).date()
    to_d = date_to or today
    from_d = to_d - timedelta(days=days - 1)

    # 날짜 → [00:00, 다음날 00:00) (타임존 포함)로 변환
    dt_from = datetime.combine(from_d, time.min).replace(tzinfo=zone)
    dt_to = datetime.combine(to_d + timedelta(days=1), time.min).replace(tzinfo=zone)

    return {
        "items": await DiaryService.emotion_stats(
            user_id=effective_user_id,
            date_from=dt_from,
            date_to=dt_to,
        )
    }


# ---------------------------------------------------------------------
# 특정 일기의 태그 목록 조회 API
# GET /diaries/{diary_id}/tags
# ---------------------------------------------------------------------
@router.get(
    "/{diary_id}/tags",
    response_model=TagListResponse,
    response_model_exclude_none=True,
)
async def get_diary_tags(diary_id: int):
    """
    특정 일기의 태그 목록 조회
    - Path Param: diary_id (일기 ID)
    - Response: TagListResponse
    """
    # 일기 존재 여부 확인
    diary = await DiaryService.get(diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="존재하지않는 다이어리입니다.")

    tags = await DiaryService.get_tags_by_diary(diary_id)

    return TagListResponse(
        items=tags,
        meta=PageMeta(page=1, page_size=len(tags), total=len(tags)),
    )


# ---------------------------------------------------------------------
# 태그명으로 일기 검색 API (diary 모듈에서 제공)
# GET /diaries/search?tags=tag1,tag2&user_id=1
# ---------------------------------------------------------------------
@router.get(
    "/search",
    response_model=DiaryListResponse,
    response_model_exclude_none=True,
)
async def search_diaries_by_tags(
    tags: Optional[str] = Query(
        None, description="검색할 태그명들 (쉼표로 구분, 예: 'tag1,tag2')"
    ),
    user_id: Optional[int] = Query(None, description="특정 사용자 ID로 필터링"),
    main_emotion: Optional[MainEmotionType] = Query(
        None, description="주요 감정 라벨로 필터링"
    ),
    date_from: Optional[datetime] = Query(None, description="조회 시작일 (YYYY-MM-DD)"),
    date_to: Optional[datetime] = Query(None, description="조회 종료일 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="페이지 번호(1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수(최대 100)"),
):
    """
    태그명으로 일기 검색 (diary 모듈에서 제공)
    - Query Params: tags (쉼표 구분), user_id, main_emotion, date_from, date_to, page, page_size
    - Response: DiaryListResponse
    """
    # 태그 파싱
    tag_names = []
    if tags:
        tag_names = [tag.strip() for tag in tags.split(",") if tag.strip()]

    raw_items, total = await DiaryService.search_by_tags(
        tag_names=tag_names,
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

    # 어떤 타입이 오든 리스트 요약으로 변환
    items: list[DiaryListItem] = [_as_list_item(it) for it in (raw_items or [])]

    return DiaryListResponse(
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


# ---------------------------------------------------------------------
# 특정 일기에 태그 추가/제거 API
# POST /diaries/{diary_id}/tags
# ---------------------------------------------------------------------
@router.post(
    "/{diary_id}/tags",
    response_model=TagListResponse,
    status_code=200,
)
async def add_tags_to_diary(
    diary_id: int,
    tag_names: List[str] = Query(..., description="추가할 태그명 목록"),
):
    """
    특정 일기에 태그 추가
    - Path Param: diary_id (일기 ID)
    - Query Param: tag_names (추가할 태그명들)
    - Response: 업데이트된 태그 목록
    """
    # 일기 존재 여부 확인
    diary = await DiaryService.get(diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="존재하지않는 다이어리입니다.")

    updated_tags = await DiaryService.add_tags_to_diary(diary_id, tag_names)

    return TagListResponse(
        items=updated_tags,
        meta=PageMeta(page=1, page_size=len(updated_tags), total=len(updated_tags)),
    )


# ---------------------------------------------------------------------
# 특정 일기에서 태그 제거 API
# DELETE /diaries/{diary_id}/tags
# ---------------------------------------------------------------------
@router.delete(
    "/{diary_id}/tags",
    response_model=TagListResponse,
    status_code=200,
)
async def remove_tags_from_diary(
    diary_id: int,
    tag_names: List[str] = Query(..., description="제거할 태그명 목록"),
):
    """
    특정 일기에서 태그 제거
    - Path Param: diary_id (일기 ID)
    - Query Param: tag_names (제거할 태그명들)
    - Response: 업데이트된 태그 목록
    """
    # 일기 존재 여부 확인
    diary = await DiaryService.get(diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="존재하지않는 다이어리입니다.")

    updated_tags = await DiaryService.remove_tags_from_diary(diary_id, tag_names)

    return TagListResponse(
        items=updated_tags,
        meta=PageMeta(page=1, page_size=len(updated_tags), total=len(updated_tags)),
    )
