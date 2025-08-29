import json
import re

import google.generativeai as genai

from core.config import AI_SETTINGS
from core.exceptions import AIServiceError

from .prompts import SimpleEmotionPrompts
from .schema import DiaryEmotionRequest, DiaryEmotionResponse
from ..diary.model import MainEmotion


class DiaryEmotionService:
    """일기 감정 분석 서비스"""

    def __init__(self):
        """AI 서비스 초기화"""
        genai.configure(api_key=AI_SETTINGS["google_api_key"])
        self.model = genai.GenerativeModel(AI_SETTINGS["model_name"])

    async def analyze_diary_emotion(
        self, request: DiaryEmotionRequest
    ) -> DiaryEmotionResponse:
        """
        일기 감정 분석

        Args:
            request: 일기 분석 요청

        Returns:
            DiaryEmotionResponse: 분석 결과 (DB 저장 가능한 형태)
        """
        try:
            prompt = SimpleEmotionPrompts.get_emotion_analysis_prompt(
                request.diary_content
            )

            response = self.model.generate_content(
                [SimpleEmotionPrompts.SYSTEM_PROMPT, prompt]
            )

            if not response.text:
                raise AIServiceError("감정 분석 결과가 비어있습니다.")

            analysis_data = await self._parse_ai_response(response.text)
            main_emotion = self._normalize_emotion(
                analysis_data.get("main_emotion", "중립")
            )

            return DiaryEmotionResponse(
                main_emotion=MainEmotion(main_emotion),
                emotion_analysis=analysis_data,
                confidence=analysis_data.get("confidence", 0.5),
            )

        except Exception as e:
            raise AIServiceError(f"감정 분석 중 오류: {str(e)}")

    def _normalize_emotion(self, emotion: str) -> str:
        """감정 타입 정규화"""
        emotion_lower = emotion.lower()
        if any(
            word in emotion_lower
            for word in ["긍정", "positive", "happy", "joy", "기쁨", "행복"]
        ):
            return "긍정"
        elif any(
            word in emotion_lower
            for word in ["부정", "negative", "sad", "angry", "슬픔", "분노"]
        ):
            return "부정"
        else:
            return "중립"

    async def _parse_ai_response(self, text: str) -> dict:
        """AI 응답에서 JSON 파싱"""
        try:
            json_match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    json_text = text[start:end]
                else:
                    return {
                        "main_emotion": "중립",
                        "confidence": 0.5,
                        "reason": "파싱 실패",
                    }

            return json.loads(json_text)

        except json.JSONDecodeError:
            return {
                "main_emotion": "중립",
                "confidence": 0.5,
                "reason": "JSON 파싱 실패",
            }

    def health_check(self) -> bool:
        """AI 서비스 상태 확인"""
        try:
            test_response = self.model.generate_content("안녕하세요")
            return bool(test_response.text)
        except Exception:
            return False
