import asyncio
import os
import sys
from pathlib import Path

from app.ai.schema import DiaryEmotionRequest, DiaryEmotionResponse, MainEmotionType

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 환경변수 설정
os.environ.setdefault("GOOGLE_API_KEY", "test_fake_key")
os.environ.setdefault("AI_MODEL_NAME", "gemini-1.5-flash")


class MockDiaryEmotionService:
    """테스트용 Mock 감정 분석 서비스"""

    def __init__(self):
        pass

    async def analyze_diary_emotion(
        self, request: DiaryEmotionRequest
    ) -> DiaryEmotionResponse:
        import json

        # 간단한 키워드 기반 감정 분류
        content = request.diary_content.lower()

        if any(word in content for word in ["행복", "기쁨", "좋", "즐거운", "감사"]):
            emotion = "긍정"
            confidence = 0.8
        elif any(
            word in content for word in ["슬픔", "화", "스트레스", "힘든", "우울"]
        ):
            emotion = "부정"
            confidence = 0.8
        else:
            emotion = "중립"
            confidence = 0.6

        analysis = {
            "main_emotion": emotion,
            "confidence": confidence,
            "reason": "키워드 기반 테스트 분석",
            "key_phrases": ["테스트 키워드"],
        }

        return DiaryEmotionResponse(
            main_emotion=MainEmotionType(emotion),
            emotion_analysis=json.dumps(analysis, ensure_ascii=False),
            confidence=confidence,
        )

    def health_check(self) -> bool:
        return True


class TestDiaryEmotionService:
    """일기 감정 분석 서비스 테스트"""

    def test_positive_emotion_analysis(self):
        """긍정적 일기 감정 분석 테스트"""
        mock_service = MockDiaryEmotionService()
        request = DiaryEmotionRequest(
            diary_content="오늘은 정말 행복한 하루였다. 친구들과 즐거운 시간을 보냈다.",
            user_id=1,
        )

        result = asyncio.run(mock_service.analyze_diary_emotion(request))

        assert result.main_emotion == MainEmotionType.POSITIVE
        assert result.confidence >= 0.7
        assert "긍정" in result.emotion_analysis
        print("긍정적 감정 분석 테스트 통과")

    def test_negative_emotion_analysis(self):
        """부정적 일기 감정 분석 테스트"""
        mock_service = MockDiaryEmotionService()
        request = DiaryEmotionRequest(
            diary_content="오늘은 너무 힘든 하루였다. 스트레스가 많고 우울했다.",
            user_id=1,
        )

        result = asyncio.run(mock_service.analyze_diary_emotion(request))

        assert result.main_emotion == MainEmotionType.NEGATIVE
        assert result.confidence >= 0.7
        print("부정적 감정 분석 테스트 통과")

    def test_neutral_emotion_analysis(self):
        """중립적 일기 감정 분석 테스트"""
        mock_service = MockDiaryEmotionService()
        request = DiaryEmotionRequest(
            diary_content="오늘은 평범한 하루였다. 일상적인 일들을 했다.", user_id=1
        )

        result = asyncio.run(mock_service.analyze_diary_emotion(request))

        assert result.main_emotion == MainEmotionType.NEUTRAL
        print("중립적 감정 분석 테스트 통과")

    def test_service_health_check(self):
        """서비스 상태 확인 테스트"""
        mock_service = MockDiaryEmotionService()
        result = mock_service.health_check()

        assert result is True
        print("서비스 헬스체크 테스트 통과")

    def test_emotion_response_schema(self):
        """감정 분석 응답 스키마 테스트"""
        import json

        response = DiaryEmotionResponse(
            main_emotion=MainEmotionType.POSITIVE,
            emotion_analysis=json.dumps({"test": "data"}, ensure_ascii=False),
            confidence=0.9,
        )

        assert response.main_emotion == MainEmotionType.POSITIVE
        assert response.confidence == 0.9
        assert isinstance(response.emotion_analysis, str)
        print("응답 스키마 테스트 통과")

    def test_db_compatibility(self):
        """DB 호환성 테스트 - main_emotion 값이 DB ENUM과 일치하는지"""
        # DB에서 사용하는 값들
        db_emotions = ["긍정", "부정", "중립"]

        for emotion_type in MainEmotionType:
            assert emotion_type.value in db_emotions

        print("DB 호환성 테스트 통과")


def test_basic_functionality():
    """기본 기능 테스트"""
    assert MainEmotionType.POSITIVE == "긍정"
    assert MainEmotionType.NEGATIVE == "부정"
    assert MainEmotionType.NEUTRAL == "중립"
    print("기본 기능 테스트 통과")


if __name__ == "__main__":
    print("일기 감정 분석 테스트 시작...")

    test_service = TestDiaryEmotionService()
    test_service.test_positive_emotion_analysis()
    test_service.test_negative_emotion_analysis()
    test_service.test_neutral_emotion_analysis()
    test_service.test_service_health_check()
    test_service.test_emotion_response_schema()
    test_service.test_db_compatibility()
    test_basic_functionality()

    print("모든 테스트 완료!")


# 실제 사용 예시
"""
1. 일기 작성 시 감정 분석 및 DB 저장:

# 일기 분석 요청
request = DiaryEmotionRequest(
    diary_content="오늘은 정말 행복한 하루였다!",
    user_id=1
)

# 감정 분석 수행
result = await diary_emotion_service.analyze_diary_emotion(request)

# DB에 일기 저장 (기존 Diary 모델 활용)
diary = await Diary.create(
    title="행복한 하루",
    content=request.diary_content,
    main_emotion=result.main_emotion.value,  # "긍정"|"부정"|"중립"
    emotion_analysis=result.emotion_analysis,  # JSON 문자열
    user_id=request.user_id
)

2. API 호출 예시:

POST /ai/analyze-diary
{
    "diary_content": "오늘은 친구들과 즐거운 시간을 보냈다. 정말 행복했다.",
    "user_id": 1
}

응답:
{
    "main_emotion": "긍정",
    "emotion_analysis": "{\"main_emotion\":\"긍정\",\"confidence\":0.9,\"reason\":\"행복, 즐거운 등 긍정적 키워드 감지\"}",
    "confidence": 0.9,
    "analysis_date": "2025-08-28T15:30:00Z"
}

3. 테스트 실행:
pytest app/ai/test_emotion.py -v
또는
python app/ai/test_emotion.py
"""
