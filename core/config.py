TORTOISE_ORM = {
    "connections": {"default": "postgres://diaryapi:diaryapi@db:5432/diaryapi"},
    "apps": {
        "models": {
            "models": [
                "app.diary.model",  # 다이어리 관련 모델
                "app.user.model",  # 유저 관련 모델
                "app.tag.model",  # 결제 관련 모델
                "app.notification.model", # 쉼표 안찍혀있었음
                "aerich.models",  # 꼭 포함해야 함
            ],
            "default_connection": "default",
        },
    },
}
