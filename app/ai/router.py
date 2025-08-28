from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from core.exceptions import AIServiceError
from .schema import UserPrompt, GenerateResponse
from .service import ai_service

# 라우터 생성
router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/")
async def ai_root():
    """AI 서비스 루트 엔드포인트"""
    return {"message": "AI 서비스가 정상적으로 작동 중입니다."}


@router.get("/health")
async def health_check():
    """AI 서비스 상태 확인 엔드포인트"""
    is_healthy = ai_service.health_check()
    if is_healthy:
        return {"status": "healthy", "service": "ai"}
    else:
        return JSONResponse(
            status_code=503, content={"status": "unhealthy", "service": "ai"}
        )


@router.post("/generate", response_model=GenerateResponse)
async def generate_text(user_prompt: UserPrompt):
    """
    텍스트 생성 엔드포인트

    Args:
        user_prompt (UserPrompt): 사용자 프롬프트

    Returns:
        GenerateResponse: 생성된 텍스트 응답

    Raises:
        HTTPException: AI 서비스 오류 시 500 에러
    """
    try:
        result = await ai_service.generate_text(user_prompt.prompt)
        return result

    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"예상치 못한 오류가 발생했습니다: {str(e)}"
        )
