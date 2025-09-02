from pydantic import BaseModel, Field

from app.notification.model import NotificationType


class NotificationCreateRequest(BaseModel):
    content: str = Field(..., max_length=255, description="알림 내용")
    type: NotificationType = Field(..., description="알림 타입")


class NotificationResponse(BaseModel):
    id: int
    weekday: int  # 추가
    notification_type: NotificationType
    content: str
    # 생성일, 수정일 제거

    class Config:
        orm_mode = True  # ORM 객체를 그대로 Pydantic 모델로 변환 가능


class UserNotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_id: int

    class Config:
        orm_mode = True
