from datetime import date
from typing import Optional, Sequence, Tuple

from fastapi import HTTPException
from tortoise.transactions import in_transaction

from app.notification.model import Notification, NotificationType
from app.user.auth import create_access_token, create_refresh_token
from app.user.model import User, UserNotification
from app.user.schema import UserCreate, UserLogin, UserResponse, UserUpdate
from app.user.utils import hash_password, verify_password


def _normalize_names(v: Optional[str | Sequence[str]]) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        items = [v]
    else:
        items = list(v)
    out: list[str] = []
    seen: set[str] = set()
    for s in items:
        name = str(s).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


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
    async def signup(payload: UserCreate) -> UserResponse:
        async with in_transaction() as conn:
            user = await User.create(
                email=payload.email,
                password=hash_password(payload.password),
                nickname=payload.nickname,
                username=payload.username,
                phonenumber=payload.phonenumber,
                using_db=conn,
                receive_notifications=payload.receive_notifications,  # 추가
            )

            notification_type_value: Optional[str] = None  # 임시 변수

            # 알림 수신 동의한 경우 조인 테이블 데이터 추가
            if payload.receive_notifications and payload.notification_type:
                # Enum값 인증 if문 안에서 수행
                allowed = {e.value for e in NotificationType}
                if payload.notification_type not in allowed:
                    raise HTTPException(
                        status_code=400,
                        detail=f"지원하지 않는 notification_type: {payload.notification_type}",
                    )

                # 요일 메세지
                today = date.today()
                weekday = today.weekday()

                # Notification 데이터 찾기
                notif = await Notification.get_or_none(
                    weekday=weekday,
                    notification_type=payload.notification_type,
                )
                if not notif:
                    raise HTTPException(
                        status_code=500,
                        detail="해당 요일/타입 알림 정의가 존재하지 않습니다.",
                    )

                # UserNotification 생성
                await UserNotification.create(
                    user_id=user.id, notification_id=notif.id, using_db=conn
                )
                notification_type_value = notif.notification_type

            # # ← 여기 수정
            # raw = getattr(
            #     payload, "notification_type", None
            # )  # str | list[str] | None 가정
            # names = _normalize_names(raw)
            # if names:
            #     # 허용값 집합 (Enum 쓰면 아래처럼)
            #     allowed = {e.value for e in NotificationType}
            #     invalid = [n for n in names if n not in allowed]
            #     if invalid:
            #         raise HTTPException(
            #             status_code=400,
            #             detail=f"지원하지 않는 notification_type: {invalid}",
            #         )

            # # 같은 트랜잭션으로 관계 갱신
            # await repository.replace_notifications(user, names, using_db=conn)

        return UserResponse(
            id=user.id,
            email=user.email,
            nickname=user.nickname,
            username=user.username,
            phonenumber=user.phonenumber,
            created_at=user.created_at,
            updated_at=user.updated_at,
            receive_notifications=user.receive_notifications,
            notification_type=notification_type_value,  # 수정
        )

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
    async def update_notification_settings(current_user: User, notification_type: Optional[str], receive: bool) -> None:
        """
        유저 알림 설정 수정
        - receive=False → 알림 모두 해제
        - receive=True + notification_type → 해당 요일/타입 알림으로 갱신
        """
        # 1) 알림 해제
        if not receive:
            await UserNotification.filter(user_id=current_user.id).delete()
            current_user.receive_notifications = False
            await current_user.save()
            return

        # 2) notification_type 필수 검증
        if not notification_type:
            raise HTTPException(status_code=400, detail="notification_type은 필수입니다.")

        # 3) Enum 값 검증
        allowed = {e.value for e in NotificationType}
        if notification_type not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 notification_type: {notification_type}",
            )

        # 4) 오늘 요일 기반 알림 찾기
        today = date.today()
        weekday = today.weekday()
        notif = await Notification.get_or_none(weekday=weekday, notification_type=notification_type)
        if not notif:
            raise HTTPException(
                status_code=500,
                detail="해당 요일/타입 알림 정의가 존재하지 않습니다.",
            )

        # 5) 조인 테이블(UserNotification) 업데이트
        user_notif = await UserNotification.get_or_none(user_id=current_user.id)
        if user_notif:
            user_notif.notification = notif  # ✅ relation 객체 갱신
            await user_notif.save()
            print(f"🔄 UserNotification updated: user_id={current_user.id}, notif_id={notif.id}")
        else:
            created = await UserNotification.create(
                user=current_user,
                notification=notif,
            )
            print(f"✅ UserNotification created: {created}")

        # 6) User 테이블 값 갱신
        current_user.receive_notifications = True
        await current_user.save()

    @staticmethod
    async def delete_user(current_user: User) -> None:
        """
        - 현재 사용자 삭제
        """
        await current_user.delete()
