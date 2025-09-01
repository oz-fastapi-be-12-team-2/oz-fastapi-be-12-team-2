from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

from app.user.routes import router as user_router

# FastAPI 인스턴스 생성
app = FastAPI(
    title="Team Project API",
    description="FastAPI + TortoiseORM 기반 팀 프로젝트 API 서버",
    version="1.0.0",
)

# 라우터 등록
app.include_router(user_router)


# DB 설정 (TortoiseORM)
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["app.user.model", "app.notification.model"]},
    generate_schemas=True,  # 앱 실행 시 자동으로 테이블 생성
    add_exception_handlers=True,
)


# 헬스 체크
@app.get("/")
async def root():
    return {"message": "API is running"}