from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.diary.model import MainEmotionType

from app.notification.api import router as notification_router
from app.notification.service import send_notifications
from app.user.model import EmotionStats, NotificationType, PeriodType, User

pytestmark = pytest.mark.asyncio
service.TEST_MODE = True


@pytest_asyncio.fixture(scope="session")
async def app() -> AsyncGenerator[FastAPI, None]:
    app = FastAPI(title="Test Notification API")
    app.include_router(notification_router)

    # Tortoise 초기화
    await Tortoise.init(
        config={
            "connections": {"default": "sqlite://:memory:"},
            "apps": {
                "models": {
                    "models": [
                        "app.user.model",
                        "app.tag.model",
                        "app.diary.model",
                        "app.notification.model",
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
    yield app
    await Tortoise.close_connections()


@pytest_asyncio.fixture(scope="session")
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def test_user() -> AsyncGenerator[User, None]:
    # 모든 테스트에서 공유할 유저 생성
    user = await User.create(
        email="test@naver.com",
        password="tester1234",
        username="테스터",
        nickname="tester",
        phonenumber="010-8393-9324",
        receive_notifications=True,
        notification_type=NotificationType.EMAIL.value,
        push_token="dummy_token",
    )
    yield user


@pytest_asyncio.fixture(scope="session")
async def test_emotionstat(test_user: User) -> AsyncGenerator[EmotionStats, None]:
    # 모든 테스트에서 공유할 유저 생성
    emotionstat = await EmotionStats.create(
        user_id=test_user.id,
        period_type=PeriodType.WEEKLY.value,
        emotion_type=MainEmotionType.NEGATIVE.value,
        type=MainEmotionType.NEGATIVE,
        frequency=5,
    )
    yield emotionstat


async def test_send_notifications(
    client: AsyncClient, test_user: User, test_emotionstat: EmotionStats
):
    notifications = await send_notifications()
    assert notifications
    assert notifications[0].content is not None
    assert notifications[0].notification_type == test_user.notification_type


async def test_create_notification_endpoint(client: AsyncClient):
    response = await client.post(
        "/notifications/",
        json={"content": "테스트 알림", "notification_type": "PUSH"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


async def test_get_notifications_endpoint(client: AsyncClient, test_user: User):
    response = await client.get(f"/notifications/{test_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


async def test_push_notification(
    client: AsyncClient, test_user: User, test_emotionstat: EmotionStats, capsys
):
    # notification_type을 PUSH로 변경
    test_user.notification_type = NotificationType.PUSH
    await test_user.save()

    payload = {"content": "푸쉬 테스트", "notification_type": "PUSH"}
    response = await client.post("/notifications/", json=payload)

    assert response.status_code == 200
    captured = capsys.readouterr()
    assert "[PUSH]" in captured.out


async def test_sms_notification(
    client: AsyncClient, test_user: User, test_emotionstat: EmotionStats, capsys
):
    # notification_type을 SMS로 변경
    test_user.notification_type = NotificationType.SMS
    await test_user.save()

    payload = {"content": "문자 테스트", "notification_type": "SMS"}
    response = await client.post("/notifications/", json=payload)
    assert response.status_code == 200
    captured = capsys.readouterr()
    assert "[SMS]" in captured.out


async def test_email_notification(
    client: AsyncClient, test_user: User, test_emotionstat: EmotionStats, capsys
):
    # notification_type을 EMAIL로 변경
    test_user.notification_type = NotificationType.EMAIL
    await test_user.save()

    payload = {"content": "이메일 테스트", "notification_type": "EMAIL"}
    response = await client.post("/notifications/", json=payload)
    assert response.status_code == 200
    captured = capsys.readouterr()
    assert "[EMAIL]" in captured.out
