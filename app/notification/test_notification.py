import pytest
from httpx import AsyncClient
from app.notification.service import send_notifications

from app.main import app
from app.user.model import NotificationType, User


@pytest.mark.asyncio
async def test_send_notifications(db):
    # given: 알림 수신 동의한 사용자 준비
    user = await User.create(
        username="tester",
        email="tester@example.com",
        phone_number="+821012345678",
        receive_notifications=True,
        notification_type=NotificationType.PUSH,  # PUSH / SMS / EMAIL 가능
        push_token="dummy_token",
    )

    # when: send_notifications 실행
    notifications = await send_notifications()

    # then: Notification이 최소 1개 이상 생성되었는지 확인
    assert notifications
    assert notifications[0].content is not None
    assert notifications[0].notification_type == user.notification_type


@pytest.mark.asyncio
async def test_create_notification_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/notifications/",
            json={"content": "테스트 알림", "notification_type": "PUSH"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_get_notifications_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 유저 ID 1번 기준 (테스트 DB에 맞게 수정 필요)
        response = await ac.get("/notifications/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_push_notification(monkeypatch):
    """
    PUSH 알림 테스트
    """

    # 실제 발송 함수 대신 print만 확인
    async def fake_send_push(user, message: str):
        print(f"[TEST-PUSH] to {user.nickname}: {message}")

    monkeypatch.setattr("notifications.send_push_notification", fake_send_push)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {"content": "푸쉬 테스트", "notification_type": "PUSH"}
        response = await ac.post("/notifications/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "알림이 생성되었습니다."


@pytest.mark.asyncio
async def test_sms_notification(monkeypatch):
    """
    SMS 알림 테스트
    """

    async def fake_send_sms(user, message: str):
        print(f"[TEST-SMS] to {user.nickname}: {message}")

    monkeypatch.setattr("notifications.send_sms", fake_send_sms)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {"content": "문자 테스트", "notification_type": "SMS"}
        response = await ac.post("/notifications/", json=payload)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_email_notification(monkeypatch):
    """
    EMAIL 알림 테스트
    """

    async def fake_send_email(user, message: str):
        print(f"[TEST-EMAIL] to {user.nickname}: {message}")

    monkeypatch.setattr("notifications.send_email", fake_send_email)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {"content": "이메일 테스트", "notification_type": "EMAIL"}
        response = await ac.post("/notifications/", json=payload)

    assert response.status_code == 200
