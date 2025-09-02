from app.notification.model import Notification, NotificationType

WEEKDAY_MESSAGES = {
    0: "한 주의 시작, 많이 힘드셨죠? 하지만 잘 해내셨으니 앞으로도 잘 하실거에요! 💪",
    1: "조금 지치셨나요? 남은 날들은 즐거운 일만 가득할 거에요. 🌿",
    2: "벌써 반 이상 왔습니다! 조금만 더 힘내봐요. 📝",
    3: "오늘도 많이 힘드셨죠? 내일만 지나면 주말이다! 힘든 마음을 챙겨보세요. 🧘",
    4: "주말이 다가옵니다. 부정적 감정을 놓아주세요. 🎵",
    5: "이번 주 부정적 감정이 많았다면, 주말에 휴식하세요. ☕",
    6: "다음 주를 위해 감정을 정리하고 준비하세요. 🌸",
}


# notification table에 초기 데이터 저장, 최초 1회 실행
async def seed_notifications():
    exists = await Notification.exists()
    if exists:
        print("✅ Notification seed already exists, skipping…")
        return

    for weekday, message in WEEKDAY_MESSAGES.items():
        for notif_type in NotificationType:  # PUSH, EMAIL, SMS
            await Notification.create(
                weekday=weekday, notification_type=notif_type, content=message
            )
    print("🌱 Notification seed inserted")
