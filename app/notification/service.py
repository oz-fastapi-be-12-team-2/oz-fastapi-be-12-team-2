import os
import smtplib
from datetime import date, datetime, time
from email.mime.text import MIMEText

from dotenv import load_dotenv

from app.diary.model import MainEmotion
from app.notification.model import NotificationType
from app.notification.respository import create_notification
from app.user.model import EmotionStats, PeriodType, User

# .env 읽기
load_dotenv()


async def check_weekly_negative_emotions(user_id: int) -> bool:
    """
    주간 단위 부정적 감정 5회 이상 기록 여부 체크
    """

    today = date.today()
    start = datetime.combine(today, time.min)  # 00:00:00
    end = datetime.combine(today, time.max)  # 23:59:59.999999

    stats = await EmotionStats.get_or_none(
        user_id=user_id,
        period_type=PeriodType.WEEKLY.value,
        created_at__gte=start,
        created_at__lt=end,
        emotion_type=MainEmotion.NEGATIVE.value,
    )
    return stats is not None and stats.frequency >= 5


async def send_notifications():

    WEEKDAY_MESSAGES = {
        0: "한 주의 시작, 많이 힘드셨죠? 하지만 잘 해내셨으니 앞으로도 잘 하실거에요! 💪",
        1: "조금 지치셨나요? 남은 날들은 즐거운 일만 가득할 거에요. 🌿",
        2: "벌써 반 이상 왔습니다! 조금만 더 힘내봐요. 📝",
        3: "오늘도 많이 힘드셨죠? 내일만 지나면 주말이다! 힘든 마음을 챙겨보세요. 🧘",
        4: "주말이 다가옵니다. 부정적 감정을 놓아주세요. 🎵",
        5: "이번 주 부정적 감정이 많았다면, 주말에 휴식하세요. ☕",
        6: "다음 주를 위해 감정을 정리하고 준비하세요. 🌸",
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
                content=content, notification_type=user.notification_type
            )

            if notification:
                if user.notification_type == NotificationType.PUSH:
                    await send_push_notification(user, message)
                elif user.notification_type == NotificationType.SMS:
                    await send_sms(user, message)
                elif user.notification_type == NotificationType.EMAIL:
                    await send_email(user, message)

                sent_notifications.append(notification)

    return sent_notifications


# PUSH
async def send_push_notification(user: User, message: str):
    print(f"[PUSH] to {user.nickname}: {message}")

    # # FCM(Firebase Cloud Messaging) 사용
    # if not user.push_token:
    #     return
    # payload = {
    #     "to": user.push_token,
    #     "notification": {"title": "오늘의 감정 알림", "body": message},
    # }
    # # aiohttp 또는 httpx로 FCM API 호출
    # async with httpx.AsyncClient() as client:
    #     await client.post("https://fcm.googleapis.com/fcm/send", json=payload,
    #                       headers={"Authorization": f"key={FCM_SERVER_KEY}"})


# SMS
async def send_sms(user: User, message: str):
    print(f"[SMS] to {user.nickname}: {message}")

    # # Twilio 사용
    # from twilio.rest import Client
    # client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # client.messages.create(
    #     to=user.phone_number,
    #     from_=TWILIO_PHONE_NUMBER,
    #     body=message
    # )


# EMAIL
async def send_email(user: User, message: str):
    EMAIL = os.getenv("EMAIL_HOST_USER", "")
    PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    HOST = os.getenv("EMAIL_HOST", "")
    PORT = int(os.getenv("EMAIL_PORT", "587"))

    msg = MIMEText(message)
    msg["Subject"] = "[Diary] 힘든 하루를 보냈나요?"
    msg["From"] = EMAIL
    msg["To"] = user.email

    try:
        # SMTP 연결
        with smtplib.SMTP(HOST, PORT) as server:
            server.starttls()  # TLS 연결
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
            print("✅ 이메일 발송 성공!")
            print(f"[EMAIL] to {user.nickname}: {message}")
    except Exception as e:
        print("❌ 이메일 발송 실패:", e)

    # # FastAPI BackgroundTasks + aiosmtplib
    # from email.message import EmailMessage
    # import aiosmtplib
    #
    # email = EmailMessage()
    # email["From"] = SMTP_FROM
    # email["To"] = user.email
    # email["Subject"] = "오늘의 감정 알림"
    # email.set_content(message)
    #
    # await aiosmtplib.send(
    #     email,
    #     hostname=SMTP_HOST,
    #     port=SMTP_PORT,
    #     username=SMTP_USER,
    #     password=SMTP_PASSWORD,
    #     start_tls=True,
    # )
