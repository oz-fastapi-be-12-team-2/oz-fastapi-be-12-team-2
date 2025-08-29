import json
from datetime import datetime
from typing import Any, Iterable, Optional

from tortoise.transactions import in_transaction

from app.diary.model import Diary, Image
from app.diary.schema import DiaryCreate, EmotionAnalysis, TagIn
from app.tag.model import Tag


def _dumps_ea(ea: Optional[EmotionAnalysis | dict[str, Any]]) -> Optional[str]:
    """
    EmotionAnalysis(Pydantic)이나 dict를 DB 저장용 JSON 문자열로 변환
    """
    if ea is None:
        return None
    if isinstance(ea, dict):
        return json.dumps(ea, ensure_ascii=False)
    return json.dumps(ea.model_dump(exclude_none=True), ensure_ascii=False)


# -----------------get_or_create------------------------------------------------------------
# CREATE
# -----------------------------------------------------------------------------
async def create(payload: DiaryCreate) -> Diary:
    diary = await Diary.create(
        title=payload.title,
        content=payload.content,
        main_emotion=payload.main_emotion,
        emotion_analysis=_dumps_ea(payload.emotion_analysis),
        user_id=payload.user_id,
    )

    # 태그 처리: TagIn 객체 리스트
    if payload.tags:
        tag_objs = []
        for t in payload.tags:
            tag, _ = await Tag.get_or_create(tag_name=t.name)
            tag_objs.append(tag)
        if tag_objs:
            await diary.tags.add(*tag_objs)

    # 이미지 처리
    if payload.images:
        for i, url in enumerate(payload.images, start=1):
            await Image.create(diary=diary, order=i, image=url)

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
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
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
async def update_partially(diary: Diary, patch: dict[str, Any]) -> Diary:
    """
    단순 필드 부분 업데이트 (트랜잭션 내부에서 호출 가능)
    """
    for k, v in patch.items():
        setattr(diary, k, v)
    await diary.save()
    return diary


async def replace_tags(diary: Diary, tags: list[TagIn]) -> None:
    await diary.tags.clear()
    for t in tags:
        tag, _ = await Tag.get_or_create(tag_name=t.name)
        await diary.tags.add(tag)


async def replace_images(diary: Diary, urls: Iterable[str]) -> None:
    """
    이미지 전체 교체: 기존 삭제 후 (order=1..n) 재생성
    """
    async with in_transaction():
        await Image.filter(diary=diary).delete()
        for i, url in enumerate(urls, start=1):
            await Image.create(
                diary=diary, order=i, image=url
            )  # 필드명이 url이면 image→url로


# -----------------------------------------------------------------------------
# DELETE
# -----------------------------------------------------------------------------
async def delete(diary: Diary) -> None:
    """
    Diary 삭제 (관련 이미지/조인 테이블은 CASCADE에 의해 제거)
    """
    await diary.delete()
