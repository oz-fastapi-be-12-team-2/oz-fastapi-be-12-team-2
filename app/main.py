from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from tortoise import Tortoise
from tortoise.exceptions import DBConnectionError

from app.ai.api import router as ai_router
from app.diary.api import router as diary_router
from app.notification.api import router as notification_router
from app.notification.seed import seed_notifications
from app.tag.api import router as tag_router
from app.user.api import router as user_router
from core.config import TORTOISE_ORM


# ─────────────────────────────────────────────────────────────
# Lifespan: DB 초기화/종료
# ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    attempts = int(os.getenv("DB_CONNECT_RETRY", "10"))
    delay = float(os.getenv("DB_CONNECT_DELAY", "1.0"))
    generate_schemas = os.getenv("DB_GENERATE_SCHEMAS", "true").lower() == "true"

    for i in range(1, attempts + 1):
        try:
            await Tortoise.init(config=TORTOISE_ORM)
            if generate_schemas:
                await Tortoise.generate_schemas()
            print("✅ DB 연결 및 초기화 성공")

            # Notification 시드 실행
            await seed_notifications()

            break
        except DBConnectionError:
            if i == attempts:
                print(f"❌ DB 연결 실패: {attempts}회 시도 후 중단")
                break
            print(f"⏳ DB 연결 재시도 {i}/{attempts}…")
            await asyncio.sleep(delay)

    yield

    await Tortoise.close_connections()
    print("👋 DB 연결 종료")


# ─────────────────────────────────────────────────────────────
# 앱 생성
# ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="FastAPI with AI Service",
    description="Gemini API를 사용하는 FastAPI 애플리케이션",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},  # Swagger에서 인증 유지
)

# CORS (필요 시 환경변수로 제어)
DEFAULT_ORIGINS = ["http://localhost", "http://localhost:3000", "http://127.0.0.1:3000"]
EXTRA_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*DEFAULT_ORIGINS, *EXTRA_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# Swagger 보안 스키마 (Bearer + Cookie)
# ─────────────────────────────────────────────────────────────
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    security_schemes = openapi_schema.setdefault("components", {}).setdefault(
        "securitySchemes", {}
    )
    # Bearer (JWT)
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    # Cookie (access_token)
    security_schemes["CookieAuth"] = {
        "type": "apiKey",
        "in": "cookie",
        "name": "access_token",
    }

    # 전역 보안 요구사항: Bearer 또는 Cookie 중 하나면 OK
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"CookieAuth": []},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# FastAPI.openapi는 “메서드”라서 재할당하면 안 된다고 해서 ignore 추가
app.openapi = custom_openapi  # type: ignore[method-assign]


# ─────────────────────────────────────────────────────────────
# 라우터 등록
# ─────────────────────────────────────────────────────────────
app.include_router(user_router)
app.include_router(diary_router)
app.include_router(tag_router)
app.include_router(ai_router)
app.include_router(notification_router)
# 라우터 순서 변경


# ─────────────────────────────────────────────────────────────
# 기본 엔드포인트
# ─────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {"message": "Gemini API를 사용하는 FastAPI 서버입니다."}


# ─────────────────────────────────────────────────────────────
# 로컬 실행 (uvicorn app.main:app --reload)
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "true").lower() == "true",
    )
