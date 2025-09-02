import uuid
from datetime import date, datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.diary.model import MainEmotionType
from app.notification import service
from app.notification.api import router as notification_router
from app.notification.model import Notification, NotificationType
from app.notification.seed import seed_notifications
from app.notification.service import get_notification_targets, send_notifications
from app.user.model import EmotionStats, PeriodType, User, UserNotification

pytestmark = pytest.mark.asyncio
service.TEST_MODE = True

# TODO : test coverage 올리기 -- 현재 60%


@pytest_asyncio.fixture
async def app() -> AsyncGenerator[FastAPI, None]:
    app = FastAPI(title="Test Notification API")
    app.include_router(notification_router)

    # Tortoise 초기화 (in-memory sqlite)
    await Tortoise.init(
        config={
            "connections": {"default": "sqlite://:memory:"},
            "apps": {
                "models": {
                    "models": [
                        "app.user.model",
                        "app.diary.model",
                        "app.notification.model",
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

    await seed_notifications()

    yield app
    await Tortoise.close_connections()


@pytest_asyncio.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user() -> User:
    unique = uuid.uuid4().hex[:6]
    user = await User.create(
        email=f"test_{unique}@example.com",
        password="hashed_pw",
        username="테스터",
        nickname=f"tester_{unique}",
        phonenumber="01012345678",
        receive_notifications=True,
    )

    # 조인 생성
    weekday = date.today().weekday()
    notif = await Notification.get(  # ✅ seed 데이터에서 가져오기
        weekday=weekday,
        notification_type=NotificationType.EMAIL,
    )
    await UserNotification.create(user=user, notification=notif)  # ✅ 조인 생성
    return user


@pytest_asyncio.fixture
async def test_emotionstat(test_user: User) -> EmotionStats:
    stat = await EmotionStats.create(
        user_id=test_user.id,
        period_type=PeriodType.WEEKLY.value,
        emotion_type=MainEmotionType.NEGATIVE.value,
        created_at=datetime.now(),
        frequency=5,
    )
    return stat


@pytest.mark.asyncio
async def test_get_targets_and_send(
    client: AsyncClient, test_user: User, test_emotionstat: EmotionStats
):
    # 1. 대상자 조회
    response = await client.get("/notifications/targets")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "targets" in data
    assert isinstance(data["targets"], list)

    # 최소 1명 이상 대상자 있어야 함
    assert any(t["user_id"] == test_user.id for t in data["targets"])

    # 2. 발송
    response = await client.post("/notifications/send")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "sent" in data
    assert any(s["user_id"] == test_user.id for s in data["sent"])


@pytest.mark.asyncio
async def test_notification_types(
    client: AsyncClient, test_user: User, test_emotionstat: EmotionStats, capsys
):
    weekday = date.today().weekday()

    for notif_type in [
        NotificationType.PUSH,
        NotificationType.SMS,
        NotificationType.EMAIL,
    ]:
        # 마스터 알림 가져오기 (이미 seed 데이터에 있어야 함)
        notif = await Notification.get(
            weekday=weekday,
            notification_type=notif_type,
        )

        # 유저-알람 연결 갱신
        await UserNotification.update_or_create(
            defaults={"notification": notif},
            user=test_user,
        )

        # 대상자 조회 & 전송
        targets = await get_notification_targets()
        await send_notifications(targets)

        captured = capsys.readouterr()
        assert f"[{notif_type.value}]" in captured.out
