from __future__ import annotations

from typing import Optional, Sequence, Tuple

from app.diary.schema import DiaryListItem, to_diary_list_item_from_model
from app.tag import repository
from app.tag.schema import TagCreate, TagResponse, to_tag_response


# ---------------------------------------------------------------------
# 서비스 계층 (비즈니스 로직 담당)
# 컨트롤러(api.py)와 DB(repository.py) 사이에서 중간 역할
# ---------------------------------------------------------------------
class TagService:
    @staticmethod
    async def create(payload: TagCreate) -> TagResponse:
        """
        태그 생성 서비스
        - 중복 태그명 검사 및 생성
        """
        # 중복 체크
        existing = await repository.get_by_name(payload.name)
        if existing:
            raise ValueError(f"이미 존재하는 태그명입니다: {payload.name}")

        tag = await repository.create(payload)
        return to_tag_response(tag)

    @staticmethod
    async def get(tag_id: int) -> Optional[TagResponse]:
        """
        태그 단건 조회 서비스 (diary_count 포함)
        """
        tag = await repository.get_by_id(tag_id, prefetch_diaries=True)
        if not tag:
            return None

        return to_tag_response(tag)

    @staticmethod
    async def get_by_name(name: str) -> Optional[TagResponse]:
        """
        태그명으로 태그 조회 서비스
        """
        tag = await repository.get_by_name(name)
        if not tag:
            return None

        await tag.fetch_related("diaries")
        return to_tag_response(tag)

    @staticmethod
    async def list(
            *,
            name: Optional[str] = None,
            page: int = 1,
            page_size: int = 20,
    ) -> Tuple[Sequence[TagResponse], int]:
        """
        태그 목록 조회 서비스
        """
        tags, total = await repository.list_tags(
            name=name,
            page=page,
            page_size=page_size,
        )

        tag_responses = [to_tag_response(tag) for tag in tags]
        return tag_responses, total

    @staticmethod
    async def get_diaries_by_tag(
            tag_id: int,
            *,
            page: int = 1,
            page_size: int = 20,
    ) -> Tuple[Sequence[DiaryListItem], int]:
        """
        특정 태그가 붙은 일기 목록 조회 서비스
        """
        diaries, total = await repository.get_diaries_by_tag_id(
            tag_id=tag_id,
            page=page,
            page_size=page_size,
        )

        diary_items = [to_diary_list_item_from_model(diary) for diary in diaries]
        return diary_items, total

    @staticmethod
    async def get_diaries_by_tag_name(
            tag_name: str,
            *,
            page: int = 1,
            page_size: int = 20,
    ) -> Tuple[Sequence[DiaryListItem], int]:
        """
        특정 태그명이 붙은 일기 목록 조회 서비스
        """
        diaries, total = await repository.get_diaries_by_tag_name(
            tag_name=tag_name,
            page=page,
            page_size=page_size,
        )

        diary_items = [to_diary_list_item_from_model(diary) for diary in diaries]
        return diary_items, total

    @staticmethod
    async def delete(tag_id: int) -> bool:
        """
        태그 삭제 서비스
        """
        tag = await repository.get_by_id(tag_id)
        if not tag:
            return False

        await repository.delete_tag(tag)
        return True

    @staticmethod
    async def get_or_create_by_name(name: str) -> TagResponse:
        """
        태그명으로 조회하거나 생성하는 서비스
        - 일기 생성/수정 시 태그 처리용
        """
        tag, created = await repository.get_or_create_by_name(name)
        if not created:
            await tag.fetch_related("diaries")

        return to_tag_response(tag)

    @staticmethod
    async def get_popular_tags(limit: int = 10) -> Sequence[TagResponse]:
        """
        인기 태그 목록 조회 서비스
        """
        tags = await repository.get_popular_tags(limit=limit)
        return [to_tag_response(tag) for tag in tags]

    @staticmethod
    async def get_tag_stats() -> dict[str, int]:
        """
        태그 통계 서비스
        - 전체 태그 수, 사용 중인 태그 수 등
        """
        all_tags = await repository.list_tags(page=1, page_size=10000)
        total_tags = all_tags[1]

        used_tags = 0
        for tag in all_tags[0]:
            if getattr(tag, 'diaries', None) and len(tag.diaries) > 0:
                used_tags += 1

        return {
            "total_tags": total_tags,
            "used_tags": used_tags,
            "unused_tags": total_tags - used_tags,
        }

    @staticmethod
    async def delete_unused_tags() -> int:
        """
        사용하지 않는 태그들(diary_count = 0) 일괄 삭제
        Returns: 삭제된 태그 수
        """
        # 사용하지 않는 태그들 찾기
        unused_tags = await repository.get_unused_tags()

        deleted_count = 0
        for tag in unused_tags:
            await repository.delete_tag(tag)
            deleted_count += 1

        return deleted_count

    @staticmethod
    async def get_admin_stats() -> dict:
        """
        관리자용 태그 통계
        """
        # 전체 태그 수
        all_tags, total_tags = await repository.list_tags(page=1, page_size=10000)

        # 사용 중인 태그 수 계산
        used_tags = 0
        unused_tags = 0
        tag_usage_stats = []

        for tag in all_tags:
            diary_count = len(getattr(tag, 'diaries', []))
            if diary_count > 0:
                used_tags += 1
                tag_usage_stats.append({
                    "id": tag.id,
                    "name": tag.name,
                    "diary_count": diary_count
                })
            else:
                unused_tags += 1

        # 인기 태그 TOP 10
        popular_tags = sorted(tag_usage_stats, key=lambda x: x['diary_count'], reverse=True)[:10]

        # 평균 사용량
        avg_usage = sum(t['diary_count'] for t in tag_usage_stats) / len(tag_usage_stats) if tag_usage_stats else 0

        return {
            "total_tags": total_tags,
            "used_tags": used_tags,
            "unused_tags": unused_tags,
            "average_diary_count_per_tag": round(avg_usage, 2),
            "popular_tags": popular_tags,
            "can_cleanup_count": unused_tags,
        }

    @staticmethod
    async def force_delete(tag_id: int, admin_user_id: int) -> bool:
        """
        강제 삭제 (사용 중인 태그도 삭제)
        - 관리자 전용
        - 로그 기록
        """
        tag = await repository.get_by_id(tag_id, prefetch_diaries=True)
        if not tag:
            return False

        diary_count = len(getattr(tag, 'diaries', []))

        # 삭제 전 로그 기록 (실제 구현시에는 proper logging 사용)
        print(f"[FORCE DELETE] Admin {admin_user_id} deleting tag '{tag.name}' (used in {diary_count} diaries)")

        await repository.delete_tag(tag)
        return True

    @staticmethod
    async def merge_tags(source_tag_id: int, target_tag_id: int, admin_user_id: int) -> bool:
        """
        태그 병합 기능
        - source_tag의 모든 일기를 target_tag로 옮기고 source_tag 삭제
        - 중복 태그 정리할 때 유용
        """
        source_tag = await repository.get_by_id(source_tag_id, prefetch_diaries=True)
        target_tag = await repository.get_by_id(target_tag_id, prefetch_diaries=True)

        if not source_tag or not target_tag:
            return False

        # source_tag를 사용하는 모든 일기 가져오기
        source_diaries = getattr(source_tag, 'diaries', [])

        # 각 일기의 태그를 업데이트
        for diary in source_diaries:
            # 일기의 태그 목록에서 source_tag 제거하고 target_tag 추가
            current_tag_names = [getattr(tag, 'name', '') for tag in getattr(diary, 'tags', [])]

            # source 태그 제거
            if source_tag.name in current_tag_names:
                current_tag_names.remove(source_tag.name)

            # target 태그 추가 (중복 방지)
            if target_tag.name not in current_tag_names:
                current_tag_names.append(target_tag.name)

            # 태그 교체
            await repository.replace_tags(diary, current_tag_names)

        # source_tag 삭제
        await repository.delete_tag(source_tag)

        print(f"[TAG MERGE] Admin {admin_user_id} merged '{source_tag.name}' -> '{target_tag.name}' ({len(source_diaries)} diaries affected)")

        return True