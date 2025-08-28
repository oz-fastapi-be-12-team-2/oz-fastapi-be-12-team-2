import google.generativeai as genai
from core.exceptions import AIServiceError
from core.config import AI_SETTINGS
from .schema import GenerateResponse


class AIService:
    """AI 서비스 클래스"""

    def __init__(self):
        """AI 서비스 초기화"""
        # Gemini API 설정
        genai.configure(api_key=AI_SETTINGS["google_api_key"])
        self.model = genai.GenerativeModel(AI_SETTINGS["model_name"])

    async def generate_text(self, prompt: str) -> GenerateResponse:
        """
        프롬프트를 기반으로 텍스트 생성

        Args:
            prompt (str): 텍스트 생성을 위한 프롬프트

        Returns:
            GenerateResponse: 생성된 텍스트 응답

        Raises:
            AIServiceError: AI 서비스 관련 오류
        """
        try:
            # Gemini API를 호출하여 텍스트 생성
            response = self.model.generate_content(prompt)

            # 응답 검증
            if not response.text:
                raise AIServiceError("생성된 텍스트가 비어있습니다.")

            return GenerateResponse(response=response.text)

        except Exception as e:
            raise AIServiceError(f"텍스트 생성 중 오류가 발생했습니다: {str(e)}")

    def health_check(self) -> bool:
        """
        AI 서비스 상태 확인

        Returns:
            bool: 서비스 정상 여부
        """
        try:
            # 간단한 테스트 프롬프트로 상태 확인
            test_response = self.model.generate_content("Hello")
            return bool(test_response.text)
        except Exception:
            return False


# 싱글톤 인스턴스
ai_service = AIService()
