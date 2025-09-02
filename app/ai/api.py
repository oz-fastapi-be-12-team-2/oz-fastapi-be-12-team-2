from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from core.exceptions import AIServiceError

from .schema import DiaryEmotionRequest, DiaryEmotionResponse
from .service import DiaryEmotionService

router = APIRouter(prefix="/ai", tags=["AI - 감정 분석"])


@router.get("/")
async def ai_root():
    """AI 감정 분석 서비스 루트"""
    return {
        "message": "일기 감정 분석 AI 서비스",
        "features": [
            "일기 감정 분석 (긍정/부정/중립)",
            "감정 통계",
            "서비스 상태 확인",
        ],
    }


@router.get("/health")
async def health_check():
    """AI 서비스 상태 확인"""
    is_healthy = DiaryEmotionService.health_check()
    if is_healthy:
        return {"status": "healthy", "service": "diary_emotion_analysis"}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "service": "diary_emotion_analysis"},
        )


@router.post("/analyze-diary", response_model=DiaryEmotionResponse)
async def analyze_diary_emotion(request: DiaryEmotionRequest):
    """
    일기 감정 분석

    - 전체적인 감정을 긍정/부정/중립으로 분류
    - 분석 결과를 JSON으로 반환
    - DB의 main_emotion, emotion_analysis 필드에 저장 가능

    Returns:
        main_emotion: "긍정"|"부정"|"중립" (DB 저장용)
        emotion_analysis: 상세 분석 결과 JSON 문자열
        confidence: 분석 신뢰도 (0-1)
    """
    try:
        service = DiaryEmotionService()
        result = await service.analyze_diary_emotion(request)
        return result

    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예상치 못한 오류: {str(e)}")


@router.post("/test-emotion")
async def test_emotion_analysis():
    """감정 분석 테스트"""
    sample_diary = """
오늘은 친구들과 함께 카페에 갔다. 오랜만에 만나서 이야기하니 정말 즐거웠다.
새로운 프로젝트에 대해서도 얘기했는데, 모두가 응원해줘서 힘이 났다.
저녁에는 가족과 함께 맛있는 저녁을 먹었다. 행복한 하루였다.
"""

    request = DiaryEmotionRequest(diary_content=sample_diary, user_id=1)

    return await analyze_diary_emotion(request)


# @router.get("/stats/{user_id}")
# async def get_emotion_stats(user_id: int, period: str = "daily"):
#     """
#     사용자 감정 통계 조회
#     TODO: 실제 EmotionStats 모델과 연동 필요
#     """
#     from typing import Dict

#     mock_stats: Dict[str, int] = {
#         "긍정": 15,
#         "부정": 8,
#         "중립": 5,
#     }

#     return EmotionStatsResponse(
#         user_id=user_id,
#         period_type=period,
#         stats=mock_stats,
#         total_count=28,
#         dominant_emotion="긍정",
#     )
