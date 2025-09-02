# notification/api/notification_router.py
from typing import List

from fastapi import APIRouter

from app.notification.repository import get_notifications_for_user
from app.notification.schema import (
    NotificationResponse,
    UserNotificationResponse,
)
from app.notification.service import (
    get_notification_targets,
    list_notifications,
    send_notifications,
)
from app.user.model import UserNotification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications():
    """
    Notification 테이블의 요일×타입별 알림 정의 전체 조회
    """
    return await list_notifications()


@router.get("/targets")
async def list_notification_targets():
    """
    발송 대상자 조회 (알림 없으면 생성/갱신 후 반환)
    """
    targets = await get_notification_targets()
    if not targets:
        return {"message": "📭 발송 대상 없음", "targets": []}

    # 직렬화 가능한 데이터로 변환
    result = [
        {
            "user_id": user.id,
            "nickname": user.nickname,
            "notification_type": notif_type,
            "message": message,
        }
        for (user, message, notif_type) in targets
    ]
    return {"count": len(result), "targets": result}


@router.post("/send")
async def send_notifications_endpoint():
    """
    실제 알림 발송
    """
    targets = await get_notification_targets()
    if not targets:
        return {"message": "📭 발송 대상 없음", "sent": []}

    sent = await send_notifications(targets)
    count = len(sent)
    return {"message": f"✅ {count}명에게 알림 발송 완료", "sent": sent}


@router.get("/users", response_model=List[UserNotificationResponse])
async def get_user_notifications_endpoint():
    """
    UserNotification 조인 테이블 전체 조회
    """
    rows = await UserNotification.all()
    return [
        UserNotificationResponse(
            id=row.id,
            user_id=row.user_id,
            notification_id=row.notification_id,
        )
        for row in rows
    ]


@router.get(
    "/users/{user_id}", response_model=NotificationResponse
)  # 응답모델 리스트 -> 단일 응답 모델
async def get_notifications_endpoint(user_id: int):
    """
    특정 사용자의 알림 조회
    """
    notifications = await get_notifications_for_user(user_id)
    return notifications


# TODO : 토큰 인증? 같은 거 추가하기
