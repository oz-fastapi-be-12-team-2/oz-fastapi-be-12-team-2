from enum import Enum
from typing import Dict, Optional, Any

from pydantic import BaseModel, Field

from app.diary.model import MainEmotion


class PeriodType(str, Enum):
    """통계 기간 타입"""

    DAILY = "daily"
    WEEKLY = "weekly"


class DiaryEmotionRequest(BaseModel):
    """일기 감정 분석 요청"""

    diary_content: str = Field(..., description="일기 내용", min_length=10)
    user_id: int = Field(..., description="사용자 ID")


class DiaryEmotionResponse(BaseModel):
    """일기 감정 분석 응답"""

    main_emotion: MainEmotion = Field(..., description="주요 감정")
    emotion_analysis: Optional[dict[str, Any]] = Field(..., description="분석 결과 JSON 문자열")
    confidence: float = Field(..., description="분석 신뢰도", ge=0, le=1)


class EmotionStatsResponse(BaseModel):
    """감정 통계 응답"""

    user_id: int
    period_type: str
    stats: Dict[str, int] = Field(..., description="감정별 빈도")
    total_count: int = Field(..., description="전체 일기 수")
    dominant_emotion: str = Field(..., description="주요 감정")


class AIErrorResponse(BaseModel):
    """AI 에러 응답 스키마"""

    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 에러 정보")
