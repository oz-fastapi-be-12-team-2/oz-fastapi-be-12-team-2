from tortoise.transactions import in_transaction

from app.notification.model import Notification, NotificationType
from app.user.model import User


async def create_notification(
    content: str, notification_type: NotificationType
) -> Notification | None:
    users = await User.filter(receive_notifications=True).all()
    if not users:
        return None  # 알림 발송 대상이 없으면 None 반환

    notification = await Notification.create(
        content=content, notification_type=notification_type
    )
    await notification.user.add(*users)
    return notification


async def get_notifications_for_user(user_id: int) -> list[Notification]:
    user = await User.get(id=user_id)
    return await user.notifications.all()


async def replace_notifications(
    user: User,
    notification_types: str,
    using_db=None,
) -> None:
    """
    - user의 기존 notification_types 관계를 모두 제거하고
    - 새로 전달받은 notification_types와 연결

    Args:
        user: User 객체
        notification_types: NotificationType id 리스트 (예: [1,2,3])
        using_db: 트랜잭션 연결 (서비스에서 in_transaction()으로 전달)
    """
    # 1) 문자열 정규화 + 빈 값 제거
    norm_names = notification_types

    # 관계만 깔끔히 재구축하고 싶다면 트랜잭션으로 감싸도 OK
    async with in_transaction():
        # 2) 기존 관계 제거

        await user.fetch_related("notifications")
        await user.notifications.clear()

        if not norm_names:
            return  # 더 할 일 없음

        # 3) 이미 존재하는 것 조회
        if isinstance(norm_names, str):
            names = [norm_names]
        else:
            names = list(norm_names)  # 이미 시퀀스면 그대로 리스트화

        # 5) 최종 확정 세트 재조회(= 전부 '저장된' 객체)
        final_objs = await Notification.filter(notification_type__in=names)

        # 6) 저장된 모델만 add (None 불가)
        if final_objs:
            await user.notifications.add(*final_objs)
