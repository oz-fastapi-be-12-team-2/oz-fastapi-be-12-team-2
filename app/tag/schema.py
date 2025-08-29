from typing import List

from pydantic import BaseModel, Field


class TagBase(BaseModel):
    tag_name: str = Field(..., min_length=1, max_length=50, description="태그 이름")


class TagCreate(TagBase):
    """태그 생성 요청"""
    pass


class TagResponse(TagBase):
    """태그 응답"""
    tag_id: int

    class Config:
        from_attributes = True


class TagWithCountResponse(TagResponse):
    """사용 횟수가 포함된 태그 응답"""
    diary_count: int = Field(0, description="이 태그를 사용한 일기 수")


class TagSearchResponse(BaseModel):
    """태그 검색 응답"""
    tags: List[TagResponse]
    total: int


class PopularTagsResponse(BaseModel):
    """인기 태그 응답"""
    tags: List[TagWithCountResponse]