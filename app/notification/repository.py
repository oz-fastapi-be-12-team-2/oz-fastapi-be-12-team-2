from model import Notification

from app.user.model import User


async def create_notification(content: str, alert_type: str) -> Notification:
    users = await User.filter(receive_notifications=True).all()
    if not users:
        return None  # 알림 발송 대상이 없으면 None 반환

    notification = await Notification.create(content=content, alert_type=alert_type)
    await notification.user.add(*users)
    return notification


async def get_notifications_for_user(user_id: int) -> list[Notification]:
    user = await User.get(id=user_id)
    return await user.notifications.all()
