from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.tag.schema import PopularTagsResponse, TagSearchResponse, TagWithCountResponse
from app.tag.service import TagService

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("/search", response_model=TagSearchResponse)
async def search_tags(
    q: str = Query(..., min_length=1, description="검색할 태그 이름"),
    limit: int = Query(20, ge=1, le=100, description="최대 결과 수"),
):
    """태그 검색"""
    return await TagService.search_tags(q, limit)


@router.get("/popular", response_model=PopularTagsResponse)
async def get_popular_tags(
    limit: int = Query(10, ge=1, le=50, description="인기 태그 개수")
):
    """인기 태그 조회 (사용 빈도 순)"""
    return await TagService.get_popular_tags(limit)


@router.get("/users/{user_id}", response_model=List[TagWithCountResponse])
async def get_user_tags(
    user_id: int, limit: int = Query(50, ge=1, le=200, description="최대 태그 수")
):
    """특정 사용자가 사용한 태그들"""
    tags = await TagService.get_user_tags(user_id, limit)
    if not tags:
        raise HTTPException(status_code=404, detail="No tags found for this user")
    return tags


@router.delete("/cleanup")
async def cleanup_unused_tags():
    """사용되지 않는 태그 정리 (관리자용)"""
    deleted_count = await TagService.cleanup_unused_tags()
    return {"message": f"{deleted_count}개의 사용되지 않는 태그가 삭제되었습니다."}
