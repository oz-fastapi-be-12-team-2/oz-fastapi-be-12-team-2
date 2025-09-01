import pytest
from httpx import AsyncClient

from app.user.model import User
from app.user.utils import hash_password


@pytest.mark.asyncio
async def test_signup_and_login(async_client: AsyncClient):
    # 회원가입
    resp = await async_client.post(
        "/users/signup",
        json={
            "email": "test@example.com",
            "password": "password123",
            "nickname": "tester",
            "username": "테스트유저",
            "phonenumber": "010-1234-5678",
            "notification_types": ["SMS"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"

    # 로그인
    resp = await async_client.post(
        "/users/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens


@pytest.mark.asyncio
async def test_get_profile(async_client: AsyncClient):
    # 먼저 유저 생성
    user = await User.create(
        email="profile@example.com",
        password=hash_password("password123"),
        nickname="프로필유저",
        username="김성수",
        phonenumber="010-9999-8888",
    )

    # 로그인해서 토큰 받기
    resp = await async_client.post(
        "/users/login",
        json=user,
    )
    tokens = resp.json()
    access_token = tokens["access_token"]

    # 프로필 조회
    resp = await async_client.get(
        "/users/me",
        cookies={"access_token": access_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "profile@example.com"


@pytest.mark.asyncio
async def test_update_profile(async_client: AsyncClient):
    # 유저 생성
    user = await User.create(
        email="update@example.com",
        password=hash_password("password123"),
        nickname="업데이트유저",
        username="update김성수",
        phonenumber="010-7777-6666",
    )

    # 로그인
    resp = await async_client.post(
        "/users/login",
        json=user,
    )
    tokens = resp.json()
    access_token = tokens["access_token"]

    # 프로필 수정 (PATCH)
    resp = await async_client.patch(
        "/users/me",
        json={"nickname": "수정됨"},
        cookies={"access_token": access_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["nickname"] == "수정됨"


@pytest.mark.asyncio
async def test_delete_user(async_client: AsyncClient):
    # 유저 생성
    user = await User.create(
        email="delete@example.com",
        password=hash_password("password123"),
        nickname="삭제유저",
        username="delete김성수",
        phonenumber="010-5555-4444",
    )

    # 로그인
    resp = await async_client.post(
        "/users/login",
        json=user,
    )
    tokens = resp.json()
    access_token = tokens["access_token"]

    # 계정 삭제
    resp = await async_client.delete(
        "/users/me",
        cookies={"access_token": access_token},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Deleted successfully"

    # DB 확인
    assert await User.filter(email="delete@example.com").first() is None
