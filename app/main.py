import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.exceptions import DBConnectionError

from app.ai.router import router as ai_router
from app.user.routes import router as user_router  # 유저 라우터 추가
from core.config import TORTOISE_ORM

DATABASE_URL = "postgresql+asyncpg://diaryapi:diaryapi@localhost:5432/diaryapi"


@asynccontextmanager
async def lifespan(app: FastAPI):
    attempt = 0
    max_attempts = 10

    while attempt < max_attempts:
        try:
            # Tortoise 초기화 - DB 연결 시도
            await Tortoise.init(
                config=TORTOISE_ORM,
            )
            # 필요한 경우 스키마 자동 생성 (프로덕션에선 마이그레이션 권장)
            await Tortoise.generate_schemas()
            print("DB 연결 및 초기화 성공!")
            break
        except DBConnectionError:
            attempt += 1
            if attempt == max_attempts:
                print(f"DB 연결 실패! {max_attempts}번 시도 후 종료.")
                break
            print(f"DB 연결 시도 중... {attempt}/{max_attempts}번")
            await asyncio.sleep(1)

    yield  # FastAPI 앱 실행

    # 앱 종료 시 DB 연결 닫기
    await Tortoise.close_connections()


app = FastAPI(
    title="FastAPI with AI Service",
    description="Gemini API를 사용하는 FastAPI 애플리케이션",
    version="1.0.0",
    lifespan=lifespan,
)

# lifespan check
# app.get("/lifespancheck")
# async def db_check():
# async with in_transaction() as conn:
# result = await conn.execute_query("SELECT 1")
# return {"db_ok": result[0][0] == 1}

# Gemini api
# AI 라우터 등록
app.include_router(ai_router)
app.include_router(user_router, prefix="/users", tags=["Users"])  # 유저 라우터 추가

@app.get("/")
def read_root():
    return {"message": "Gemini API를 사용하는 FastAPI 서버입니다."}
