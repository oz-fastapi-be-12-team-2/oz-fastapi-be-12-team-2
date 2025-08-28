from datetime import datetime, timedelta

from repository import create_notification

from app.diary.model import Diary  # 일기 모델
from app.user.model import User

NEGATIVE_KEYWORDS = [
    "슬픔",
    "우울",
    "불안",
    "짜증",
    "분노",
]  # TODO : emotion_stat diary에서 구현된 것 어떻게 가져올지...


async def get_negative_emotion_count(
    user_id: int, start: datetime, end: datetime
) -> int:
    """
    특정 기간(user_id, start~end) 부정 감정 키워드 수 조회
    """
    count = await Diary.filter(
        user_id=user_id,
        created_at__gte=start,
        created_at__lte=end,
        content__icontains_any=NEGATIVE_KEYWORDS,
    ).count()
    return count


# TODO : emotion_stat 부분 체크
async def check_weekly_negative_emotions(user_id: int) -> bool:
    """
    주간 단위 부정적 감정 5회 이상 기록 여부 체크
    """
    week_ago = datetime.utcnow() - timedelta(days=7)

    # Diary.content에 NEGATIVE_KEYWORDS가 포함된 기록을 필터링
    count = await Diary.filter(
        user_id=user_id,
        created_at__gte=week_ago,
        content__icontains_any=NEGATIVE_KEYWORDS,  # Tortoise ORM 키워드 포함 검색
    ).count()

    return count >= 5


async def send_notifications():
    users = await User.filter(receive_notifications=True).all()

    for user in users:
        if await check_weekly_negative_emotions(user.id):
            content = "이번 주 부정적인 감정 기록이 많습니다."  # TODO : 말해보카처럼 응원해주는 메세지 여러개 작성해서 랜덤으로 발송하게 하기
            await create_notification(
                content=content, alert_type=user.notification_type
            )  # TODO: 알림 타입을 사용자가 설정 가능하도록 구현하기
