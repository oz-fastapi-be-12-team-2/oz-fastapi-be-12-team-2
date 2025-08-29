import os

import firebase_admin  # type: ignore
from dotenv import load_dotenv
from firebase_admin import credentials, messaging  # type: ignore

load_dotenv()

# Firebase 서비스 계정 정보 환경변수 로드
firebase_config = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": (os.getenv("FIREBASE_PRIVATE_KEY") or "").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
}

# Firebase 초기화 (한 번만 실행되도록)
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)


async def send_push_notification(token: str, title: str, body: str):
    """
    FCM 푸시 알림 발송
    :param token: 클라이언트 디바이스 FCM 토큰
    :param title: 알림 제목
    :param body: 알림 내용
    """
    if not token:
        raise ValueError("FCM 토큰이 필요합니다")

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
    )

    # 실제 전송
    response = messaging.send(message)

    # 서버 로그 출력
    print(
        f"[FCM PUSH SENT] title='{title}', body='{body}', token='{token}', response='{response}'"
    )

    return response


# 로컬에서 테스트용 실행
if __name__ == "__main__":
    import asyncio

    # 실제 발송 테스트: 나중에 앱에서 발급받은 토큰 사용
    dummy_token = "여기에_실제_발급된_FCM_TOKEN_넣기"
    asyncio.run(send_push_notification(dummy_token, "테스트 제목", "테스트 메시지"))
