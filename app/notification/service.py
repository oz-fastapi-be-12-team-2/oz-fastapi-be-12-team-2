import os
import smtplib
from datetime import date, datetime, time
from email.mime.text import MIMEText

from dotenv import load_dotenv
from solapi import SolapiMessageService  # type: ignore
from solapi.model import RequestMessage  # type: ignore

from app.diary.model import MainEmotionType
from app.notification.model import NotificationType
from app.notification.repository import create_notification
from app.user.model import EmotionStats, PeriodType, User

load_dotenv()

TEST_MODE = False  # 기본값: 실제 발송


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
        emotion_type=MainEmotionType.NEGATIVE.value,
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
                content=content,
                notification_type=user.notifications.__getattribute__(
                    "notification_type"
                ),
            )

            # 테스트 모드에서는 프린트만 실행
            if notification:
                if TEST_MODE:
                    print(
                        f"[{user.notification_type.value}] to {user.nickname}: {message}"
                    )
                else:
                    if user.notification_type == NotificationType.PUSH:
                        await send_push_notification(user, message)
                    elif user.notification_type == NotificationType.SMS:
                        await send_sms(user, message)
                    elif user.notification_type == NotificationType.EMAIL:
                        await send_email(user, message)

                sent_notifications.append(notification)

    return sent_notifications


# SMS
async def send_sms(user: User, message: str):
    # API 키와 API Secret을 설정
    API_KEY = os.getenv("COOLSMS_API_KEY")
    API_SECRET = os.getenv("COOLSMS_API_SECRET")
    SENDER_NUMBER = os.getenv("COOLSMS_SENDER")
    RECIEVER_NUMBER = user.phonenumber.replace("-", "")

    message_service = SolapiMessageService(api_key=API_KEY, api_secret=API_SECRET)

    # 단일 메시지 모델을 생성합니다
    message = RequestMessage(
        from_=SENDER_NUMBER,  # 발신번호
        to=RECIEVER_NUMBER,  # 수신번호
        text=message,
    )

    # 메시지를 발송합니다
    try:
        message_service.send(message)
        print("✅ 메시지 발송 성공!")
        print(f"[SMS] to {user.nickname}: {message}")
    except Exception as e:
        print(f"❌ 메시지 발송 실패: {str(e)}")


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


# PUSH
async def send_push_notification(user: User, message: str):
    print(f"[PUSH] to {user.nickname}: {message}")
    # Firebase 푸쉬 알림을 위해서는 앱에서 발급받는 토큰 필요 -> 서버만 있는 상태에서는 사용 불가

    # # Firebase 초기화
    # if not firebase_admin._apps:
    #     cred = credentials.Certificate({
    #         "type": "service_account",
    #         "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    #         "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    #         "private_key": (os.getenv("FIREBASE_PRIVATE_KEY") or "").replace("\\n", "\n"),
    #         "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    #         "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    #         "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    #         "token_uri": "https://oauth2.googleapis.com/token",
    #         "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    #         "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    #     })
    #     firebase_admin.initialize_app(cred)
    #
    # """
    # :param user: FCM 토큰을 가진 사용자 객체 (user.fcm_token)
    # :param message: 알림 내용
    # """
    # if not getattr(user, "fcm_token", None):
    #     print("❌ 푸시 발송 실패: FCM 토큰 없음")
    #     return
    #
    # msg = messaging.Message(
    #     notification=messaging.Notification(
    #         title="[Diary] 힘든 하루를 보냈나요?",
    #         body=message
    #     ),
    #     token=user.fcm_token,
    # )
    #
    # try:
    #     response = messaging.send(msg)
    #     print("✅ 푸시 발송 성공!")
    #     print(f"[FCM] to {user.nickname}: {message}, response={response}")
    # except Exception as e:
    #     print("❌ 푸시 발송 실패:", e)
