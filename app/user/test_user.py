# app/user/test_user.py
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.notification.model import NotificationType
from app.user.api import router as user_router
from app.user.model import User
from app.user.utils import hash_password


@pytest_asyncio.fixture(scope="session")
async def app() -> AsyncGenerator[FastAPI, None]:
    """
    테스트용 FastAPI 앱. /users 라우터 장착.
    """
    app = FastAPI(title="Test User API")
    app.include_router(user_router)
    yield app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    - Tortoise ORM: SQLite in-memory 초기화
    - httpx AsyncClient 구성
    """
    os.environ["TESTING"] = "1"

    # ※ 반드시 Notification 모델을 포함해서 초기화해야 함
    await Tortoise.init(
        config={
            "connections": {"default": "sqlite://:memory:"},
            "apps": {
                "models": {
                    "models": [
                        "app.user.model",  # User, EmotionStats, UserNotification
                        "app.notification.model",  # Notification
                        "app.diary.model",
                        "app.tag.model",
                        "aerich.models",
                    ],
                    "default_connection": "default",
                }
            },
            "use_tz": True,
            "timezone": "Asia/Seoul",
        }
    )

    await Tortoise.generate_schemas()

    from app.notification.model import Notification

    await Notification.get_or_create(
        notification_type="SMS", defaults={"is_enabled": True}
    )
    await Notification.get_or_create(
        notification_type="EMAIL", defaults={"is_enabled": True}
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_signup_and_login(client: AsyncClient):
    """
    - 회원가입 201
    - 로그인 200 및 토큰 2종
    """

    # 회원가입
    resp = await client.post(
        "/users/signup",
        json={
            "email": "test@example.com",
            "password": "password123",
            "nickname": "tester",
            "username": "테스트유저",
            "phonenumber": "010-1234-5678",
            "notification_types": [NotificationType.SMS],
        },
    )
    assert resp.status_code in (200, 201)  # 라우터 설정에 따라 200/201 둘 다 허용
    data = resp.json()
    assert data["email"] == "test@example.com"

    # 로그인
    resp = await client.post(
        "/users/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient):
    """
    - 유저 직접 생성
    - 로그인 후 쿠키로 /users/me 호출
    """
    # 유저 생성
    await User.create(
        email="profile@example.com",
        password=hash_password("password123"),
        nickname="프로필유저",
        username="김성수",
        phonenumber="010-9999-8888",
    )

    # 로그인해서 토큰 수령
    resp = await client.post(
        "/users/login",
        json={"email": "profile@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    access_token = tokens["access_token"]

    # 프로필 조회 (쿠키로 인증)
    resp = await client.get("/users/me", cookies={"access_token": access_token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "profile@example.com"

    # 검증 추가
    assert "receive_notifications" in data
    assert "notifications" in data
    assert isinstance(data["receive_notifications"], bool)
    assert isinstance(data["notifications"], list)


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    """
    - 유저 직접 생성
    - 로그인 후 nickname PATCH
    """
    await User.create(
        email="update@example.com",
        password=hash_password("password123"),
        nickname="업데이트유저",
        username="update김성수",
        phonenumber="010-7777-6666",
    )

    # 로그인
    resp = await client.post(
        "/users/login",
        json={"email": "update@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    access_token = tokens["access_token"]

    # 프로필 수정
    resp = await client.patch(
        "/users/me",
        json={"nickname": "수정됨"},
        cookies={"access_token": access_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["nickname"] == "수정됨"


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient):
    """
    - 유저 직접 생성
    - 로그인 후 /users/me DELETE
    """
    await User.create(
        email="delete@example.com",
        password=hash_password("password123"),
        nickname="삭제유저",
        username="delete김성수",
        phonenumber="010-5555-4444",
    )

    # 로그인
    resp = await client.post(
        "/users/login",
        json={"email": "delete@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    access_token = tokens["access_token"]

    # 삭제
    resp = await client.delete("/users/me", cookies={"access_token": access_token})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Deleted successfully"

    # DB 확인
    assert await User.filter(email="delete@example.com").first() is None
