from __future__ import annotations

from typing import Optional, Sequence, Tuple

from tortoise.queryset import QuerySet

from app.diary.model import Diary
from app.tag.model import Tag
from app.tag.schema import TagCreate


# -----------------------------------------------------------------------------
# CREATE
# -----------------------------------------------------------------------------
async def create(payload: TagCreate, using_db=None) -> Tag:
    """
    태그 생성
    """
    tag = await Tag.create(
        name=payload.name.strip(),
        using_db=using_db,
    )
    return tag


async def get_or_create_by_name(name: str, using_db=None) -> Tuple[Tag, bool]:
    """
    태그명으로 조회하거나 생성
    - Returns: (Tag 객체, 생성 여부)
    """
    return await Tag.get_or_create(
        name=name.strip(),
        using_db=using_db,
    )


# -----------------------------------------------------------------------------
# READ
# -----------------------------------------------------------------------------
async def get_by_id(tag_id: int, *, prefetch_diaries: bool = False) -> Optional[Tag]:
    """
    ID로 태그 단건 조회
    - prefetch_diaries=True면 diary_count 계산 가능
    """
    qs = Tag.filter(id=tag_id)
    if prefetch_diaries:
        qs = qs.prefetch_related("diaries")
    return await qs.first()


async def get_by_name(name: str) -> Optional[Tag]:
    """
    이름으로 태그 단건 조회
    """
    return await Tag.get_or_none(name=name.strip())


async def list_tags(
        *,
        name: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
) -> Tuple[Sequence[Tag], int]:
    """
    태그 목록 조회 (검색 + 페이징)
    """
    qs: QuerySet[Tag] = Tag.all().prefetch_related("diaries")

    # 이름으로 검색 (부분 일치)
    if name is not None:
        qs = qs.filter(name__icontains=name.strip())

    # 총 개수
    total = await qs.count()

    # 페이징 + 정렬 (이름순)
    items = await qs.order_by("name").offset((page - 1) * page_size).limit(page_size)

    return items, total


async def get_diaries_by_tag_id(
        tag_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
) -> Tuple[Sequence[Diary], int]:
    """
    특정 태그 ID가 붙은 일기 목록 조회
    """
    # 태그를 통해 일기들을 조회
    qs = (
        Diary.filter(tags__id=tag_id)
        .prefetch_related("tags", "images", "user")
        .distinct()
    )

    # 총 개수
    total = await qs.count()

    # 페이징 + 정렬 (최신순)
    items = await qs.order_by("-created_at").offset((page - 1) * page_size).limit(page_size)

    return items, total


async def get_diaries_by_tag_name(
        tag_name: str,
        *,
        page: int = 1,
        page_size: int = 20,
) -> Tuple[Sequence[Diary], int]:
    """
    특정 태그명이 붙은 일기 목록 조회
    """
    qs = (
        Diary.filter(tags__name=tag_name.strip())
        .prefetch_related("tags", "images", "user")
        .distinct()
    )

    # 총 개수
    total = await qs.count()

    # 페이징 + 정렬 (최신순)
    items = await qs.order_by("-created_at").offset((page - 1) * page_size).limit(page_size)

    return items, total


# -----------------------------------------------------------------------------
# UPDATE
# -----------------------------------------------------------------------------
# async def update_tag(tag: Tag, name: str) -> Tag:
#     """
#     태그 이름 수정
#     """
#     tag.name = name.strip()
#     await tag.save()
#     return tag
#
#
# # -----------------------------------------------------------------------------
# # DELETE
# # -----------------------------------------------------------------------------
# async def delete_tag(tag: Tag) -> None:
#     """
#     태그 삭제
#     - 일기와의 관계는 ManyToMany이므로 관계만 해제되고 일기는 유지됨
#     """
#     await tag.delete()


# -----------------------------------------------------------------------------
# UTILITY
# -----------------------------------------------------------------------------
# async def count_diaries_by_tag_id(tag_id: int) -> int:
#     """
#     특정 태그가 사용된 일기 개수 조회
#     """
#     return await Diary.filter(tags__id=tag_id).count()


async def get_popular_tags(limit: int = 10) -> Sequence[Tag]:
    """
    인기 태그 조회 (일기 수 기준 상위 N개)
    """
    # Raw SQL을 사용하거나 Python에서 계산하는 방법이 필요
    # 여기서는 간단히 모든 태그를 가져와서 Python에서 정렬
    tags = await Tag.all().prefetch_related("diaries")

    # 일기 수로 정렬
    sorted_tags = sorted(tags, key=lambda t: len(getattr(t, 'diaries', [])), reverse=True)

    return sorted_tags[:limit]
