from fastapi import APIRouter, Depends, HTTPException, Response

from app.user.auth import create_access_token, create_refresh_token, get_current_user
from app.user.model import User, UserNotification
from app.user.schema import (
    LogoutResponse,
    NotificationUpdateRequest,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.user.service import UserService
from app.user.utils import verify_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate):
    exists = await User.filter(email=user.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await UserService.signup(user)


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
    notif = await UserNotification.get_or_none(user_id=current_user.id).prefetch_related("notification")

    return {
        "id": current_user.id,
        "email": current_user.email,
        "nickname": current_user.nickname,
        "username": current_user.username,
        "phonenumber": current_user.phonenumber,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "receive_notifications": current_user.receive_notifications,
        "notification_type": notif.notification.notification_type
    }


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


# 알림 설정 수정
@router.patch("/me/notifications")
async def update_my_notifications(
    payload: NotificationUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    내 알림 설정 수정 (알림 수신 여부 + 알림 타입)
    """
    await UserService.update_notification_settings(
        current_user=current_user,
        notification_type=payload.notification_type,
        receive=payload.receive_notifications,
    )
    return {"message": "알림 설정이 업데이트되었습니다."}


# 내 계정 삭제
@router.delete("/me")
async def delete_user(current_user: User = Depends(get_current_user)):
    await current_user.delete()
    return {"message": "Deleted successfully"}
