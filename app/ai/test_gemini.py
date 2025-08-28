import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 테스트용 환경변수 설정 (import 전에!)
os.environ.setdefault("GOOGLE_API_KEY", "test_fake_api_key_12345")
os.environ.setdefault("AI_MODEL_NAME", "gemini-1.5-flash")
os.environ.setdefault("AI_MAX_TOKENS", "1000")
os.environ.setdefault("AI_TEMPERATURE", "0.7")

from app.ai.service import AIService
from app.ai.schema import GenerateResponse
from app.main import app

client = TestClient(app)


class TestAIService:
    """AI 서비스 테스트"""

    @patch('app.ai.service.genai')
    async def test_generate_text_success(self, mock_genai):
        """텍스트 생성 성공 테스트"""
        # Mock 설정
        mock_response = MagicMock()
        mock_response.text = "생성된 텍스트입니다."

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # 테스트 실행
        service = AIService()
        result = await service.generate_text("테스트 프롬프트")

        # 검증
        assert isinstance(result, GenerateResponse)
        assert result.response == "생성된 텍스트입니다."

    @patch('app.ai.service.genai')
    def test_health_check(self, mock_genai):
        """헬스체크 테스트"""
        mock_response = MagicMock()
        mock_response.text = "Hello"

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        service = AIService()
        result = service.health_check()

        assert result is True


class TestAIAPI:
    """AI API 엔드포인트 테스트"""

    def test_ai_root(self):
        """AI 루트 엔드포인트 테스트"""
        response = client.get("/ai/")

        assert response.status_code == 200
        data = response.json()
        assert "AI 서비스가 정상적으로 작동 중입니다" in data["message"]

    @patch('app.ai.router.ai_service.generate_text')
    def test_generate_endpoint(self, mock_generate):
        """텍스트 생성 API 테스트"""
        mock_generate.return_value = GenerateResponse(response="AI 응답")

        response = client.post(
            "/ai/generate",
            json={"prompt": "안녕하세요"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "AI 응답"

    @patch('app.ai.router.ai_service.health_check')
    def test_health_endpoint(self, mock_health):
        """헬스체크 API 테스트"""
        mock_health.return_value = True

        response = client.get("/ai/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"