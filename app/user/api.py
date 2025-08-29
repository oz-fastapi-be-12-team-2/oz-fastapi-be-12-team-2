from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.user.routes import router as user_router

app = FastAPI(
    title="My FastAPI Project",
    description="User management and authentication API",
    version="1.0.0",
)

# CORS 설정 (필요 시)
origins = [
    "http://localhost",
    "http://localhost:3000",  # 프론트엔드 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(user_router)

# 기본 헬스체크용 엔드포인트
@app.get("/")
async def root():
    return {"message": "API is running!"}