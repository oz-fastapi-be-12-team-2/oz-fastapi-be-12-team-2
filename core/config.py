TORTOISE_ORM = {
    "connections": {"default": "postgres://diaryapi:diaryapi@db:5432/diaryapi"},
    "apps": {
        "models": {
            "models": [
                "app.diary.model",  # 다이어리 관련 모델
                "app.user.model",  # 유저 관련 모델
                "app.tag.model",  # 결제 관련 모델
                "app.notification.model",
                "aerich.models",  # 꼭 포함해야 함
            ],
            "default_connection": "default",
        },
    },
}
import os

AI_SETTINGS = {
    "google_api_key": os.getenv("GOOGLE_API_KEY"),
    "model_name": os.getenv("AI_MODEL_NAME", "gemini-1.5-flash"),
    "max_tokens": int(os.getenv("AI_MAX_TOKENS", "1000")),
    "temperature": float(os.getenv("AI_TEMPERATURE", "0.7")),
}

if not AI_SETTINGS["google_api_key"]:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
