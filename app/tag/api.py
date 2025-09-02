from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.tag.schema import (
    PageMeta,
    TagCreate,
    TagDiaryListResponse,
    TagListResponse,
    TagResponse,
)
from app.tag.service import TagService

# ---------------------------------------------------------------------
# 태그 API 라우터
# - prefix="/tags"     → 모든 경로가 /tags/... 로 시작
# - tags=["Tags"]      → Swagger UI에서 태그 그룹으로 묶임
# ---------------------------------------------------------------------
router = APIRouter(prefix="/tags", tags=["Tags"])


# ---------------------------------------------------------------------
# 태그 생성 API
# POST /tags
# ---------------------------------------------------------------------
@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(payload: TagCreate):
    """
    태그 생성
    - Body: TagCreate (name 필수)
    - Response: TagResponse
    """
    return await TagService.create(payload)


# ---------------------------------------------------------------------
# 태그 목록 조회 API
# GET /tags
# ---------------------------------------------------------------------
@router.get("", response_model=TagListResponse, response_model_exclude_none=True)
async def list_tags(
    name: Optional[str] = Query(None, description="태그명으로 검색 (부분 일치)"),
    page: int = Query(1, ge=1, description="페이지 번호(1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수(최대 100)"),
):
    """
    태그 목록 조회 (페이징)
    - Query Params: name (검색), page, page_size
    - Response: TagListResponse
    """
    items, total = await TagService.list(
        name=name,
        page=page,
        page_size=page_size,
    )

    return TagListResponse(
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


# ---------------------------------------------------------------------
# 태그 단건 조회 API
# GET /tags/{tag_id}
# ---------------------------------------------------------------------
@router.get("/{tag_id}", response_model=TagResponse, response_model_exclude_none=True)
async def get_tag(tag_id: int):
    """
    태그 단건 조회
    - Path Param: tag_id (조회할 태그 ID)
    - Response: TagResponse
    """
    result = await TagService.get(tag_id)
    if not result:
        raise HTTPException(status_code=404, detail="존재하지않는 태그입니다.")
    return result


# ---------------------------------------------------------------------
# 특정 태그가 붙은 일기 목록 조회 API
# GET /tags/{tag_id}/diaries
# ---------------------------------------------------------------------
# @router.get(
#     "/{tag_id}/diaries",
#     response_model=TagDiaryListResponse,
#     response_model_exclude_none=True,
# )
# async def get_diaries_by_tag(
#     tag_id: int,
#     page: int = Query(1, ge=1, description="페이지 번호(1부터 시작)"),
#     page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수(최대 100)"),
# ):
#     """
#     특정 태그가 붙은 일기 목록 조회
#     - Path Param: tag_id (태그 ID)
#     - Query Params: page, page_size
#     - Response: TagDiaryListResponse
#     """
#     # 태그 존재 여부 확인
#     tag = await TagService.get(tag_id)
#     if not tag:
#         raise HTTPException(status_code=404, detail="존재하지않는 태그입니다.")
#
#     diaries, total = await TagService.get_diaries_by_tag(
#         tag_id=tag_id,
#         page=page,
#         page_size=page_size,
#     )
#
#     return TagDiaryListResponse(
#         tag=tag,
#         diaries=diaries,
#         meta=PageMeta(page=page, page_size=page_size, total=total),
#     )


# ---------------------------------------------------------------------
# 태그명으로 일기 검색 API
# GET /tags/search/diaries
# ---------------------------------------------------------------------
@router.get(
    "/search-by-name/diaries",
    response_model=TagDiaryListResponse,
    response_model_exclude_none=True,
)
async def search_diaries_by_tag_name(
    tag_name: str = Query(..., description="검색할 태그명"),
    page: int = Query(1, ge=1, description="페이지 번호(1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수(최대 100)"),
):
    """
    태그명으로 일기 검색
    - Query Params: tag_name (필수), page, page_size
    - Response: TagDiaryListResponse
    """
    # 태그명으로 태그 조회
    tag = await TagService.get_by_name(tag_name)
    if not tag:
        raise HTTPException(
            status_code=404, detail=f"'{tag_name}' 태그를 찾을 수 없습니다."
        )

    diaries, total = await TagService.get_diaries_by_tag_name(
        tag_name=tag.name,
        page=page,
        page_size=page_size,
    )
    # 해당 태그의 일기가 없는 경우 추가 예외 처리
    if total == 0:
        raise HTTPException(
            status_code=404, detail=f"'{tag_name}' 태그가 붙은 일기가 없습니다."
        )

    return TagDiaryListResponse(
        tag=tag,
        diaries=list(diaries),
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


# ---------------------------------------------------------------------
# 태그 삭제 API - 일단 주석 처리 (프로젝트 진행 중 복잡도 방지)
# DELETE /tags/{tag_id}
# ---------------------------------------------------------------------
# @router.delete("/{tag_id}", status_code=204)
# async def delete_tag(tag_id: int):
#     """
#     태그 삭제 - 향후 권한 관리와 함께 구현 예정
#     """
#     ok = await TagService.delete(tag_id)
#     if not ok:
#         raise HTTPException(status_code=404, detail="Tag not found")
#     return None
