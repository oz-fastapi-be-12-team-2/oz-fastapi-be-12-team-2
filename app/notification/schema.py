from datetime import datetime

from pydantic import BaseModel, Field

from app.notification.model import NotificationType


class NotificationCreateRequest(BaseModel):
    content: str = Field(..., max_length=255, description="알림 내용")
    type: NotificationType = Field(..., description="알림 타입")


class NotificationResponse(BaseModel):
    id: int
    content: str
    type: NotificationType
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True  # ORM 객체를 그대로 Pydantic 모델로 변환 가능
