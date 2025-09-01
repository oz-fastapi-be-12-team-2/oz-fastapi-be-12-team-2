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
    names: list[str],
    using_db=None,
) -> None:

    # ① 호출자가 트랜잭션을 넘기면 그대로 사용, 없으면 내부에서 하나 만들고 '모든 쿼리'에 전달
    if using_db is None:
        async with in_transaction() as conn:
            await _replace_notifications_impl(user, names, conn)
    else:
        await _replace_notifications_impl(user, names, using_db)


async def _replace_notifications_impl(user: User, names: list[str], conn) -> None:
    # 기존 관계 제거 (반드시 같은 커넥션)
    await user.notifications.clear(using_db=conn)

    if not names:
        return

    # 존재하는 것 조회 (같은 커넥션)
    existing = await Notification.filter(notification_type__in=names).using_db(conn)
    have = {n.notification_type for n in existing}

    # 누락분 생성 (같은 커넥션)
    missing = [x for x in names if x not in have]
    if missing:
        await Notification.bulk_create(
            [Notification(notification_type=m) for m in missing],
            using_db=conn,
        )

    # 최종 객체 재조회 (같은 커넥션)
    final_objs = await Notification.filter(notification_type__in=names).using_db(conn)

    # 조인 추가 (같은 커넥션)
    if final_objs:
        await user.notifications.add(*final_objs, using_db=conn)
