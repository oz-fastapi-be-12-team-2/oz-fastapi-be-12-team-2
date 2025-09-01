from typing import Optional, Tuple

from fastapi import HTTPException
from tortoise.transactions import in_transaction

from app.notification import repository
from app.user.auth import create_access_token, create_refresh_token
from app.user.model import User
from app.user.schema import UserCreate, UserLogin, UserUpdate
from app.user.utils import hash_password, verify_password


class UserService:
    # ─────────────────────────────────────────────────────────
    # Auth & Token
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _issue_tokens(user_id: int) -> Tuple[str, str]:
        """
        주어진 user_id 기준으로 access/refresh 토큰을 발급.
        """
        access = create_access_token({"sub": str(user_id)})
        refresh = create_refresh_token({"sub": str(user_id)})
        return access, refresh

    # ─────────────────────────────────────────────────────────
    # Sign up
    # ─────────────────────────────────────────────────────────
    @staticmethod
    async def signup(payload: UserCreate) -> User:
        """
        - 비밀번호 해싱
        - 사용자 생성
        - notification_types가 있으면 연결 갱신
        """
        async with in_transaction() as conn:
            # 사용자 생성 (동일 트랜잭션 사용)
            user = await User.create(
                email=payload.email,
                password=hash_password(payload.password),
                nickname=payload.nickname,
                username=payload.username,
                phonenumber=payload.phonenumber,
                using_db=conn,
            )

            # payload 안에 notification_types가 있으면 연결 생성/치환
            types = payload.notification_types
            if types is not None:
                await repository.replace_notifications(  # ← 함수명만 교체
                    user, types, using_db=conn  # ← 변수 재사용
                )

        return user

    # ─────────────────────────────────────────────────────────
    # Login
    # ─────────────────────────────────────────────────────────
    @staticmethod
    async def login(payload: UserLogin) -> Tuple[str, str, User]:
        """
        - 이메일로 사용자 조회
        - 비밀번호 검증
        - 토큰 2종 발급
        - (access, refresh, user) 반환
        """
        user = await User.filter(email=payload.email).first()
        if not user or not verify_password(payload.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access, refresh = UserService._issue_tokens(user.id)
        return access, refresh, user

    # ─────────────────────────────────────────────────────────
    # Profile
    # ─────────────────────────────────────────────────────────
    @staticmethod
    async def get_profile(current_user: User) -> User:
        """
        - 현재 사용자 객체 그대로 반환
        """
        return current_user

    @staticmethod
    async def update_profile(current_user: User, update: UserUpdate) -> User:
        """
        - 부분 업데이트(patch)
        - password 전달 시 해싱 후 저장
        - email 변경 시 중복 체크(옵션)
        """
        update_dict = update.dict(exclude_unset=True)

        # 이메일 변경 시 중복 체크(필요 없으면 제거 가능)
        new_email: Optional[str] = update_dict.get("email")
        if new_email and new_email != current_user.email:
            dup = await User.filter(email=new_email).exclude(id=current_user.id).first()
            if dup:
                raise HTTPException(status_code=400, detail="Email already in use")

        # 비밀번호 갱신 시 해싱
        if "password" in update_dict and update_dict["password"]:
            update_dict["password"] = hash_password(update_dict["password"])

        for k, v in update_dict.items():
            setattr(current_user, k, v)

        await current_user.save()
        return current_user

    @staticmethod
    async def delete_user(current_user: User) -> None:
        """
        - 현재 사용자 삭제
        """
        await current_user.delete()
