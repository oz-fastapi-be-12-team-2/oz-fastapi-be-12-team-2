class SimpleEmotionPrompts:
    """간단한 감정 분석 프롬프트"""

    SYSTEM_PROMPT = """
당신은 일기의 전체적인 감정을 분석하는 AI입니다.
일기를 읽고 전반적인 감정을 긍정, 부정, 중립 중 하나로 분류해주세요.
"""

    @staticmethod
    def get_emotion_analysis_prompt(diary_content: str) -> str:
        return f"""
다음 일기를 분석해서 전체적인 감정을 판단해주세요.

일기 내용:
{diary_content}

다음 JSON 형식으로 응답해주세요:
{{
    "main_emotion": "긍정|부정|중립",
    "confidence": 0.85,
    "reason": "분석 근거를 간단히 설명",
    "key_phrases": ["감정을 나타내는 주요 문구들"]
}}

분석 기준:
- 긍정: 기쁨, 행복, 만족, 감사 등의 감정이 주를 이룰 때
- 부정: 슬픔, 분노, 불안, 스트레스 등의 감정이 주를 이룰 때
- 중립: 감정 표현이 적거나 긍정/부정이 섞여 있을 때
"""
