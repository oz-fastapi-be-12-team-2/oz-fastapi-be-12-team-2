from datetime import datetime

from model import NotificationType
from pydantic import BaseModel, Field


class NotificationCreateRequest(BaseModel):
    content: str = Field(..., max_length=255, description="알림 내용")
    notification_type: NotificationType = Field(..., description="알림 타입")
    # TODO : user Model에 receive_notifications 필드 추가 -- 완료
    # TODO : user schema에 receive_notifications 필드 추가?
    # TODO : user schema에 알림 수신 여부 설정 변경 스키마 추가
    # TODO : user api에 알림 수신 여부 설정 변경 엔드포인트 추가


class NotificationResponse(BaseModel):
    alert_id: int
    content: str
    notification_type: NotificationType
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True  # ORM 객체를 그대로 Pydantic 모델로 변환 가능
