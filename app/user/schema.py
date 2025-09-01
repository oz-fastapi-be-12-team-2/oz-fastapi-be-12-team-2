from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.notification.model import NotificationType


# 회원가입 시 요청 스키마
class UserCreate(BaseModel):
    email: EmailStr  # 이메일 형식 자동 검증
    password: Annotated[str, Field(min_length=8)]  # 최소 8자 이상
    nickname: Annotated[str, Field(min_length=2, max_length=20)]
    username: str
    phonenumber: Annotated[
        str, Field(pattern=r"^010-\d{4}-\d{4}$")
    ]  # 010-0000-0000 형식
    notification_types: Optional[List[NotificationType]]


# 로그인 요청 시 스키마
class UserLogin(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]  # UserCreate와 통일


# 응답용 (비밀번호 제외)
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    nickname: str
    username: str
    phonenumber: str
    created_at: datetime
    updated_at: datetime
    receive_notifications: bool  # 추가
    notifications: list          # 추가
    class Config:
        orm_mode = True  # ORM 모델과 호환 (예: SQLAlchemy, TortoiseORM)


# 토큰 발급
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


# 로그아웃 응답
class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"


# 회원정보 수정
class UserUpdate(BaseModel):
    nickname: str | None = None
    username: str | None = None
    phonenumber: str | None = None
