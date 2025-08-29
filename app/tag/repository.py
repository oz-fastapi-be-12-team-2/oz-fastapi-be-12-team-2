from typing import List, Optional

from app.tag.model import Tag


class TagRepository:
    @staticmethod
    async def get_or_create_tag(tag_name: str) -> Tag:
        """태그 이름으로 조회하거나 생성"""
        tag, created = await Tag.get_or_create(tag_name=tag_name.strip())
        return tag

    @staticmethod
    async def get_by_name(tag_name: str) -> Optional[Tag]:
        """태그 이름으로 조회"""
        return await Tag.get_or_none(tag_name=tag_name.strip())

    @staticmethod
    async def get_by_id(tag_id: int) -> Optional[Tag]:
        """태그 ID로 조회"""
        return await Tag.get_or_none(tag_id=tag_id)

    @staticmethod
    async def list_all_tags(limit: int = 100) -> List[Tag]:
        """모든 태그 조회 (사용 빈도 순)"""
        return await Tag.all().limit(limit)

    @staticmethod
    async def search_tags(query: str, limit: int = 20) -> List[Tag]:
        """PostgreSQL ILIKE를 사용한 대소문자 무시 태그 검색"""
        return await Tag.filter(tag_name__ilike=f"%{query.strip()}%").limit(limit)

    @staticmethod
    async def get_popular_tags(limit: int = 10) -> List[dict]:
        """인기 태그 조회 (다이어리 수 기준) - ORM 버전"""
        from tortoise.functions import Count

        # Tortoise ORM으로 집계 쿼리
        tags = await Tag.annotate(
            diary_count=Count('diaries')
        ).order_by('-diary_count').limit(limit)

        return [
            {
                "tag_id": tag.tag_id,
                "tag_name": tag.tag_name,
                "diary_count": tag.diary_count
            }
            for tag in tags
        ]

    @staticmethod
    async def get_user_tags(user_id: int, limit: int = 50) -> List[dict]:
        """특정 사용자가 사용한 태그들 - ORM 버전"""
        from tortoise.functions import Count

        # 사용자의 일기들과 연결된 태그들을 집계
        tags = await Tag.filter(
            diaries__user_id=user_id
        ).annotate(
            usage_count=Count('diaries', distinct=True)
        ).order_by('-usage_count').limit(limit)

        return [
            {
                "tag_id": tag.tag_id,
                "tag_name": tag.tag_name,
                "usage_count": tag.usage_count
            }
            for tag in tags
        ]

    @staticmethod
    async def delete_unused_tags() -> int:
        """사용되지 않는 태그 삭제 - ORM 버전"""
        # 일기와 연결되지 않은 태그들 찾기
        unused_tags = await Tag.filter(diaries__isnull=True)
        count = len(unused_tags)

        # 삭제 수행
        await Tag.filter(diaries__isnull=True).delete()

        return count