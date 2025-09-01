import json
from datetime import date
from typing import Any, Optional, Sequence

from tortoise.transactions import in_transaction

from app.ai.schema import DiaryEmotionResponse
from app.diary.model import Diary, DiaryTag, Image
from app.diary.schema import DiaryCreate
from app.tag.model import Tag


def _dumps_ea(ea: Optional[DiaryEmotionResponse | dict[str, Any]]) -> Optional[str]:
    """
    DiaryEmotionResponse(Pydantic)이나 dict를 DB 저장용 JSON 문자열로 변환
    """
    if ea is None:
        return None
    if isinstance(ea, dict):
        return json.dumps(ea, ensure_ascii=False)
    return json.dumps(ea.model_dump(exclude_none=True), ensure_ascii=False)


# -----------------get_or_create------------------------------------------------------------
# CREATE
# -----------------------------------------------------------------------------
async def create(payload: DiaryCreate, using_db=None) -> Diary:
    diary = await Diary.create(
        title=payload.title,
        content=payload.content,
        emotion_analysis_report=_dumps_ea(payload.emotion_analysis_report),
        user_id=payload.user_id,
        using_db=using_db,
    )
    await diary.fetch_related("images", "tags", "user")
    return diary


# -----------------------------------------------------------------------------
# READ
# -----------------------------------------------------------------------------
async def get_by_id(diary_id: int) -> Optional[Diary]:
    """
    단건 조회 (태그/이미지/유저 prefetch)
    """
    return await Diary.get_or_none(id=diary_id).prefetch_related(
        "tags", "images", "user"
    )


async def list_by_user(
    user_id: int, *, page: int = 1, page_size: int = 20
) -> tuple[list[Diary], int]:
    """
    특정 유저의 다이어리 목록 + 전체 개수 반환
    """
    qs = Diary.filter(user_id=user_id).prefetch_related("tags", "images")
    total = await qs.count()
    items = await qs.offset((page - 1) * page_size).limit(page_size)
    return items, total


async def list_by_filters(
    *,
    user_id: Optional[int] = None,
    main_emotion: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Diary], int]:
    """
    다이어리 목록 조회
    - 필터(user_id, main_emotion, 기간)를 적용해서 페이징 처리
    - created_at DESC 정렬
    """
    qs = Diary.all().prefetch_related("tags", "images", "user")

    # 조건 필터링
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if main_emotion is not None:
        qs = qs.filter(main_emotion=main_emotion)
    if date_from is not None:
        qs = qs.filter(created_at__gte=date_from)
    if date_to is not None:
        qs = qs.filter(created_at__lte=date_to)

    # 총 개수
    total = await qs.count()

    # 페이징 처리 + 정렬
    rows = (
        await qs.order_by("-created_at").offset((page - 1) * page_size).limit(page_size)
    )

    return rows, total


# -----------------------------------------------------------------------------
# UPDATE
# -----------------------------------------------------------------------------
SCALAR_UPDATABLE = {"title", "content", "main_emotion"}  # 필요한 것만 허용


async def update_partially(diary: Diary, patch: dict[str, Any]) -> Diary:
    clean: dict[str, Any] = {}
    for k, v in patch.items():
        if k in {"id", "created_at", "updated_at", "user_id"}:
            continue
        if k in {"tags", "images", "image_urls"}:
            continue  # 관계/별도 처리
        if k not in SCALAR_UPDATABLE:
            continue
        # None 무시하고 싶으면: if v is None: continue
        clean[k] = v

    for k, v in clean.items():
        setattr(diary, k, v)
    await diary.save()
    return diary


async def replace_tags(diary: Diary, names: Sequence[str], using_db=None) -> None:
    """
    태그 전체 교체.
    - 입력 문자열 배열을 정규화
    - 존재하지 않으면 생성(get_or_create)
    - 기존 연결 clear 후, 새 태그 add
    """
    # if not names:
    #     await diary.tags.clear()
    #     return

    # async with in_transaction():
    #     tag_objs: list[Tag] = []
    #     for name in names:
    #         tag, _ = await Tag.get_or_create(name=name)
    #         tag_objs.append(tag)
    #     await diary.tags.clear()
    #     await diary.tags.add(*tag_objs)

    cleaned = [n.strip() for n in (names or []) if isinstance(n, str) and n.strip()]
    await DiaryTag.filter(diary_id=diary.id).using_db(using_db).delete()
    if not cleaned:
        return
    tags: list[Tag] = []
    for nm in cleaned:
        t, _ = await Tag.get_or_create(name=nm, using_db=using_db)
        tags.append(t)
    await DiaryTag.bulk_create(
        [DiaryTag(diary_id=diary.id, tag_id=t.id) for t in tags],
        using_db=using_db,
    )


async def replace_images(diary: Diary, urls: Sequence[str], using_db=None) -> None:
    """
    이미지 전체 교체.
    - 공백 제거 + 중복 제거(원래 순서 유지)
    - 기존 이미지 삭제
    - 새 URL을 order=1..N으로 bulk insert
    """
    norm, seen = [], set()
    for u in urls:
        s = (u or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        norm.append(s)

    async with in_transaction():
        await Image.filter(diary_id=diary.id).delete()
        if norm:
            print("replace_images.norm=", norm)
            rows = [
                Image(diary_id=diary.id, url=u, order=i + 1) for i, u in enumerate(norm)
            ]
            await Image.bulk_create(rows)


# -----------------------------------------------------------------------------
# DELETE
# -----------------------------------------------------------------------------
async def delete(diary: Diary) -> None:
    """
    Diary 삭제 (관련 이미지/조인 테이블은 CASCADE에 의해 제거)
    """
    await diary.delete()


async def search_by_tags(
    *,
    tag_names: Optional[list[str]] = None,
    user_id: Optional[int] = None,
    main_emotion: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Diary], int]:
    """
    태그명으로 일기 검색
    - tag_names가 있으면 해당 태그들 중 하나라도 포함된 일기들 검색
    - 다른 필터 조건들도 함께 적용
    """
    qs = Diary.all().prefetch_related("tags", "images", "user")

    # 태그 필터링 (OR 조건: 태그 중 하나라도 매치되면)
    if tag_names:
        # 공백 제거 및 빈 값 필터링
        clean_tag_names = [name.strip() for name in tag_names if name and name.strip()]
        if clean_tag_names:
            qs = qs.filter(tags__name__in=clean_tag_names).distinct()

    # 기존 필터들
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if main_emotion is not None:
        qs = qs.filter(main_emotion=main_emotion)
    if date_from is not None:
        qs = qs.filter(created_at__gte=date_from)
    if date_to is not None:
        qs = qs.filter(created_at__lte=date_to)

    # 총 개수
    total = await qs.count()

    # 페이징 처리 + 정렬
    rows = (
        await qs.order_by("-created_at").offset((page - 1) * page_size).limit(page_size)
    )

    return rows, total


async def search_by_all_tags(
    *,
    tag_names: list[str],
    user_id: Optional[int] = None,
    main_emotion: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Diary], int]:
    """
    모든 태그를 포함하는 일기 검색 (AND 조건)
    - 지정된 모든 태그가 붙어있는 일기들만 검색
    """
    if not tag_names:
        return [], 0

    clean_tag_names = [name.strip() for name in tag_names if name and name.strip()]
    if not clean_tag_names:
        return [], 0

    qs = Diary.all().prefetch_related("tags", "images", "user")

    # 모든 태그를 포함하는 일기 찾기 (AND 조건)
    for tag_name in clean_tag_names:
        qs = qs.filter(tags__name=tag_name)

    qs = qs.distinct()

    # 기존 필터들
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if main_emotion is not None:
        qs = qs.filter(main_emotion=main_emotion)
    if date_from is not None:
        qs = qs.filter(created_at__gte=date_from)
    if date_to is not None:
        qs = qs.filter(created_at__lte=date_to)

    # 총 개수
    total = await qs.count()

    # 페이징 처리 + 정렬
    rows = (
        await qs.order_by("-created_at").offset((page - 1) * page_size).limit(page_size)
    )

    return rows, total


async def count_diaries_by_tag_name(tag_name: str) -> int:
    """
    특정 태그명이 사용된 일기 개수 반환
    """
    return await Diary.filter(tags__name=tag_name.strip()).count()


async def get_diaries_with_tag_count(
    *,
    min_tag_count: int = 1,
    user_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Diary], int]:
    """
    최소 N개 이상의 태그를 가진 일기들 조회
    """
    # Raw SQL이 필요한 복잡한 쿼리이므로 간단한 버전으로 구현
    qs = Diary.all().prefetch_related("tags", "images", "user")

    if user_id is not None:
        qs = qs.filter(user_id=user_id)

    # 모든 일기를 가져와서 Python에서 필터링 (비효율적이지만 간단)
    all_diaries = await qs.order_by("-created_at")

    # 태그 개수 조건 필터링
    filtered_diaries = []
    for diary in all_diaries:
        tags = getattr(diary, "tags", [])
        if len(tags) >= min_tag_count:
            filtered_diaries.append(diary)

    total = len(filtered_diaries)

    # 페이징 적용
    start = (page - 1) * page_size
    end = start + page_size
    page_diaries = filtered_diaries[start:end]

    return page_diaries, total
