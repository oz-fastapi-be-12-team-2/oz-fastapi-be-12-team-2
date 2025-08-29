from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# 회원가입 시 요청 스키마
class UserCreate(BaseModel):
    email: EmailStr  # 이메일 형식 자동 검증
    password: str = Field(min_length=8, description="최소 8자 이상")
    nickname: str = Field(min_length=2, max_length=20)
    username: str
    # Pydantic v2에서는 constr 대신 Field + str 권장
    # phonenumber: constr(regex=r"^010-\d{4}-\d{4}$")  # 010-0000-0000 형식
    phonenumber: str = Field(
        pattern=r"^010-\d{4}-\d{4}$", description="010-0000-0000 형식"
    )


# 로그인 요청 시 스키마
class UserLogin(BaseModel):
    email: EmailStr
    password: str


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
