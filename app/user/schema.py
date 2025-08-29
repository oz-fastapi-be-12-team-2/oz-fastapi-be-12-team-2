from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, constr


# 회원가입 시 요청 스키마
class UserCreate(BaseModel):
    email: EmailStr  # 이메일 형식 자동 검증
    password: constr(min_length=8)  # 최소 8자 이상
    nickname: constr(min_length=2, max_length=20)
    username: str
    phone: str = Field(..., pattern=r"^010-\d{4}-\d{4}$")  # 010-0000-0000 형식


# 로그인 요청 시 스키마
class UserLogin(BaseModel):
    email: EmailStr
    password: constr(min_length=8)  # UserCreate 부분과 통일했습니다.


# 응답용 (비밀번호 제외)
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    nickname: str
    username: str
    phonenumber: str
    created_at: datetime
    updated_at: datetime

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


# class UserNotificationSettingUpdate(BaseModel):
#    receive_notifications: bool = Field(..., description="알림 수신 여부")
