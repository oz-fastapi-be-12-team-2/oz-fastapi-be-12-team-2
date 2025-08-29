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
