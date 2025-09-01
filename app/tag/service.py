from typing import List

from app.tag.repository import TagRepository
from app.tag.schema import (
    PopularTagsResponse,
    TagResponse,
    TagSearchResponse,
    TagWithCountResponse,
)


class TagService:
    @staticmethod
    async def get_or_create_tags(tag_names: List[str]) -> List[TagResponse]:
        """여러 태그를 한번에 조회/생성"""
        tags = []
        for name in tag_names:
            if name and name.strip():
                tag = await TagRepository.get_or_create_tag(name.strip())
                tags.append(TagResponse.model_validate(tag))
        return tags

    @staticmethod
    async def search_tags(query: str, limit: int = 20) -> TagSearchResponse:
        """태그 검색"""
        if not query or not query.strip():
            return TagSearchResponse(tags=[], total=0)

        tags = await TagRepository.search_tags(query, limit)
        tag_responses = [TagResponse.model_validate(tag) for tag in tags]

        return TagSearchResponse(tags=tag_responses, total=len(tag_responses))

    @staticmethod
    async def get_popular_tags(limit: int = 10) -> PopularTagsResponse:
        """인기 태그 조회"""
        popular_data = await TagRepository.get_popular_tags(limit)

        tags = [
            TagWithCountResponse(
                tag_id=item["tag_id"],
                tag_name=item["tag_name"],
                diary_count=item["diary_count"],
            )
            for item in popular_data
        ]

        return PopularTagsResponse(tags=tags)

    @staticmethod
    async def get_user_tags(
        user_id: int, limit: int = 50
    ) -> List[TagWithCountResponse]:
        """사용자의 태그 사용 이력"""
        user_tag_data = await TagRepository.get_user_tags(user_id, limit)

        return [
            TagWithCountResponse(
                tag_id=item["tag_id"],
                tag_name=item["tag_name"],
                diary_count=item["usage_count"],
            )
            for item in user_tag_data
        ]

    @staticmethod
    async def cleanup_unused_tags() -> int:
        """사용되지 않는 태그 정리"""
        return await TagRepository.delete_unused_tags()
