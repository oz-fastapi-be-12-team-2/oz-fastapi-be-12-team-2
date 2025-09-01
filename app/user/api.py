from fastapi import APIRouter, Depends, HTTPException, Response

from app.user.auth import create_access_token, create_refresh_token, get_current_user
from app.user.model import User
from app.user.schema import (
    LogoutResponse,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.user.utils import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate):
    exists = await User.filter(email=user.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await User.create(
        email=user.email,
        password=hash_password(user.password),
        nickname=user.nickname,
        username=user.username,
        phonenumber=user.phonenumber,
    )
    return new_user


@router.post("/login", response_model=Token)
async def login(user: UserLogin, response: Response):
    db_user = await User.filter(email=user.email).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token({"sub": str(db_user.id)})
    refresh = create_refresh_token({"sub": str(db_user.id)})

    response.set_cookie("access_token", access, httponly=True)
    response.set_cookie("refresh_token", refresh, httponly=True)

    return Token(access_token=access, refresh_token=refresh)


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return LogoutResponse()


# 프로필 관련 기능 (회원정보 확인/수정/삭제)


# 내 프로필 조회
@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


# 내 프로필 수정
@router.patch("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
):
    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(current_user, key, value)
    await current_user.save()
    return current_user


# 내 계정 삭제
@router.delete("/me")
async def delete_user(current_user: User = Depends(get_current_user)):
    await current_user.delete()
    return {"message": "Deleted successfully"}
