from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from tortoise import Tortoise
from tortoise.exceptions import DBConnectionError
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


app = FastAPI(lifespan=lifespan)
