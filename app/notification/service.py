from datetime import datetime, timedelta, date

from repository import create_notification

from app.diary.model import EmotionStats  # noqa
from app.user.model import User



# TODO : emotion_stat 참고해서 수정
async def check_weekly_negative_emotions(user_id: int) -> bool:
    """
    주간 단위 부정적 감정 5회 이상 기록 여부 체크
    """

    today = date.today()
    stats = await EmotionStats.get_or_none(
        user_id=user_id,
        period_type="weekly",
        created_at=today,
        emotion_type="negative",
    )
    return stats is not None and stats.frequency >= 5


async def send_notifications():

    WEEKDAY_MESSAGES = {
        0: "한 주의 시작, 많이 힘드셨죠? 하지만 잘 해내셨으니 앞으로도 잘 하실거에요! 💪",
        1: "조금 지치셨나요? 남은 날들은 즐거운 일만 가득할 거에요. 🌿",
        2: "벌써 반 이상 왔습니다! 조금만 더 힘내봐요. 📝",
        3: "오늘도 많이 힘드셨죠? 내일만 지나면 주말이다! 힘든 마음을 챙겨보세요. 🧘",
        4: "금요일: 주말이 다가옵니다. 부정적 감정을 놓아주세요. 🎵",
        5: "토요일: 이번 주 부정적 감정이 많았다면, 주말에 휴식하세요. ☕",
        6: "일요일: 다음 주를 위해 감정을 정리하고 준비하세요. 🌸",
    }

    users = await User.filter(receive_notifications=True).all()
    if users is None:
        return None

    today = date.today()
    weekday = today.weekday()
    message = WEEKDAY_MESSAGES[weekday]

    sent_notifications = []
    for user in users:
        if await check_weekly_negative_emotions(user.id):
            content = message
            notification = await create_notification(
                content=content, alert_type=user.notification_type
            )  # TODO: user table 수정사항 반영하기
            if notification :
                sent_notifications.append(notification)

    return sent_notifications
