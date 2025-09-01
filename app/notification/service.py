import os
import smtplib
from datetime import date, datetime, time
from email.mime.text import MIMEText
from typing import List

from dotenv import load_dotenv
from fastapi import HTTPException
from solapi import SolapiMessageService  # type: ignore
from solapi.model import RequestMessage  # type: ignore

from app.diary.model import MainEmotionType
from app.notification import repository
from app.notification.model import Notification, NotificationType
from app.user.model import EmotionStats, PeriodType, User, UserNotification

load_dotenv()

TEST_MODE = False  # 기본값: 실제 발송


# 알림 테이블 전체 조회
async def list_notifications():
    return await repository.get_all_notifications()


# 유저-알림 조인 테이블 전체 조회
async def list_user_notifications():
    return await repository.get_user_notifications()


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


async def get_notification_targets() -> List[tuple[User, str, NotificationType]]:
    """
    발송 대상 유저 + 메시지 + 알림 타입 리스트 반환
    (유저-알람 조인 테이블을 오늘 요일/알람 타입 기준으로 업데이트)
    """
    users = await User.filter(receive_notifications=True).all()
    targets = []

    today = date.today()
    weekday = today.weekday()

    for user in users:
        if not await check_weekly_negative_emotions(user.id):
            continue

        # 유저-알람 조인 조회
        user_notif = await UserNotification.get_or_none(
            user_id=user.id
        ).prefetch_related("notification")

        if not user_notif or not user_notif.notification:
            # 유저가 아직 알림 타입을 선택하지 않은 경우 → 건너뛰기
            continue

        # 유저가 받을 알람 타입 결정
        notif_type = user_notif.notification.notification_type

        # 오늘 요일 + 타입에 맞는 마스터 알람 찾기
        notif = await Notification.get_or_none(
            weekday=weekday, notification_type=notif_type
        )
        if not notif:
            raise HTTPException(
                status_code=500,
                detail=f"알람 마스터에 정의되지 않은 알림 (weekday={weekday}, type={notif_type})",
            )

        if user_notif:
            # 이미 있으면 오늘 요일에 맞는 알람으로 교체
            if user_notif.notification_id != notif.id:
                user_notif.notification = notif
                await user_notif.save()
                print(f"🔄 UserNotification updated: user={user.id}, notif={notif.id}")
        else:
            # 없으면 새로 생성
            user_notif = await UserNotification.create(
                user=user,
                notification=notif,
            )
            print(f"✅ UserNotification created: user={user.id}, notif={notif.id}")

        # 마스터 알람의 content 그대로 사용
        message = notif.content
        targets.append((user, message, notif.notification_type))

    return targets


async def send_notifications(targets: list[tuple[User, str, NotificationType]]):
    sent = []
    for user, message, notif_type in targets:
        if TEST_MODE:
            print(f"[{notif_type}] to {user.nickname}: {message}")
        else:
            if notif_type == NotificationType.PUSH:
                await send_push_notification(user, message)
            elif notif_type == NotificationType.SMS:
                await send_sms(user, message)
            elif notif_type == NotificationType.EMAIL:
                await send_email(user, message)
        sent.append({"user_id": user.id, "nickname": user.nickname})
    return sent


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
