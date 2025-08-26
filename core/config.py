TORTOISE_ORM = {
    "connections": {"default": "postgres://diaryapi:diaryapi@localhost:5432/diaryapi"},
    "apps": {
        "models": {
            "models": [
                "app.diary.model",  # 다이어리 관련 모델
                "app.user.model",  # 유저 관련 모델
                "app.tag.model",  # 결제 관련 모델
                "app.notification.model" "aerich.models",  # 꼭 포함해야 함
            ],
            "default_connection": "default",
        },
    },
}
