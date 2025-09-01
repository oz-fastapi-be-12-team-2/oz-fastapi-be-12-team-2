import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

# .env 읽기
load_dotenv()

EMAIL = os.getenv("EMAIL_HOST_USER", "")
PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
HOST = os.getenv("EMAIL_HOST", "")
PORT = int(os.getenv("EMAIL_PORT", "587"))

# 테스트용 메시지
msg = MIMEText("이것은 SMTP 연결 테스트 이메일입니다.")
msg["Subject"] = "SMTP 연결 테스트"
msg["From"] = EMAIL
msg["To"] = EMAIL  # 본인 계정으로 테스트

try:
    # SMTP 연결
    with smtplib.SMTP(HOST, PORT) as server:
        server.starttls()  # TLS 연결
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)
        print("✅ 이메일 발송 성공!")
except Exception as e:
    print("❌ 이메일 발송 실패:", e)
