# notification/api/notification_router.py
from fastapi import APIRouter

from app.notification.repository import get_notifications_for_user
from app.notification.schema import NotificationCreateRequest, NotificationResponse
from app.notification.service import send_notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/", response_model=dict)
async def create_notification_endpoint(req: NotificationCreateRequest):
    """
    알림 생성 (receive_notifications=True 사용자 자동 선택)
    """
    notification = await send_notifications()
    if notification is None:
        return {"message": "알림 발송 대상이 없습니다."}
    return {"message": f"{len(notification)}명에게 알림 발송 완료"}


@router.get("/{user_id}", response_model=list[NotificationResponse])
async def get_notifications_endpoint(user_id: int):
    """
    특정 사용자의 알림 조회
    """
    notifications = await get_notifications_for_user(user_id)
    return notifications


# TODO : 토큰 인증? 같은 거 추가하기
