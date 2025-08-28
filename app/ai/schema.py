from pydantic import BaseModel, Field
from typing import Optional


class UserPrompt(BaseModel):
    """사용자 프롬프트 요청 스키마"""

    prompt: str = Field(..., description="생성할 텍스트를 위한 프롬프트", min_length=1)


class GenerateResponse(BaseModel):
    """텍스트 생성 응답 스키마"""

    response: str = Field(..., description="생성된 텍스트")


class AIErrorResponse(BaseModel):
    """AI 에러 응답 스키마"""

    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 에러 정보")
