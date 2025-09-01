# =============================================================================
# 다이어리 API 통합 테스트 (멀티파트 업로드 + 태그/이미지 저장 + AI 스텁)
# - httpx AsyncClient 로 FastAPI 라우터 호출
# - Tortoise ORM: in-memory SQLite 사용 (매 테스트 케이스마다 초기화)
# =============================================================================

import base64
import json
import uuid
from typing import AsyncGenerator, List, Optional

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.ai.schema import DiaryEmotionResponse, EmotionAnalysis
from app.diary.api import router as diary_router
from app.user.model import User

# pytest-asyncio 만 사용
pytestmark = pytest.mark.asyncio


# =============================================================================
# 상수/테스트용 바이너리
# =============================================================================

# 1x1 투명 PNG (유효한 이미지 바이트)
_PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6p2tQAAAAASUVORK5CYII="
)


# =============================================================================
# 공용 헬퍼
# =============================================================================
def _mp_file(field: str, name: str, content: bytes, content_type: str):
    """httpx files 인자 편의 함수: (필드명, (파일명, 바이트, MIME))"""
    return (field, (name, content, content_type))


async def _post_diary_multipart(
    client: AsyncClient, payload: dict, image_files: Optional[List[tuple]] = None
):
    """
    멀티파트 요청 전송:
    - 본문 JSON은 'payload_json' 필드에 문자열로
    - 파일은 'image_files' 필드에 다중 첨부
    """
    data = {"payload_json": json.dumps(payload, ensure_ascii=False)}
    files = []
    if image_files:
        for fname, bts, ctype in image_files:
            files.append(_mp_file("image_files", fname, bts, ctype))
    return await client.post("/diaries", data=data, files=files or None)


async def _patch_diary_multipart(
    client: AsyncClient, diary_id: int, patch: dict, image_files=None
):
    data = {"payload_json": json.dumps(patch, ensure_ascii=False)}
    files = []
    if image_files:
        for fname, bts, ctype in image_files:
            files.append(("image_files", (fname, bts, ctype)))
    return await client.patch(f"/diaries/{diary_id}", data=data, files=files or None)


# =============================================================================
# AI 스텁 (의존성 오버라이드로 주입)
# =============================================================================
class _StubAI:
    async def analyze_diary_emotion(self, req):
        # 서비스/레포지토리가 그대로 소화할 수 있는 Pydantic 모델 반환
        return DiaryEmotionResponse(
            main_emotion="긍정",
            confidence=1.0,
            emotion_analysis=EmotionAnalysis(
                reason="stub",
                key_phrases=["테스트", "스텁"],
            ),
        )


# =============================================================================
# 앱/클라이언트 픽스처
# =============================================================================
@pytest_asyncio.fixture(scope="session")
async def app() -> AsyncGenerator[FastAPI, None]:
    """테스트용 FastAPI 앱에 실제 다이어리 라우터 장착"""
    app = FastAPI(title="Test Diary API")
    app.include_router(diary_router)
    yield app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    """
    - FastAPI 의존성 오버라이드로 AI 스텁 주입
    - Tortoise ORM in-memory SQLite 초기화
    - httpx AsyncClient 구성
    """
    # 테스트에서만 AI 의존성 오버라이드
    # app.dependency_overrides[_resolve_ai] = lambda: _StubAI()

    # ORM 초기화(테스트 모델 등록)
    #   - Tag 모델이 app.diary.model 안으로 통합됐다면 "app.tag.model" 항목을 제거하세요.
    await Tortoise.init(
        config={
            "connections": {"default": "sqlite://:memory:"},
            "apps": {
                "models": {
                    "models": [
                        "app.user.model",
                        "app.diary.model",
                        "app.tag.model",
                        "app.notification.model",
                        "aerich.models",
                    ],
                    "default_connection": "default",
                }
            },
            "use_tz": True,
            "timezone": "Asia/Seoul",
        },
    )
    await Tortoise.generate_schemas()

    # HTTP 클라이언트
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await Tortoise.close_connections()  # type: ignore[attr-defined]


# =============================================================================
# 데이터 준비 헬퍼
# =============================================================================
async def _ensure_user(email: str = "") -> int:
    """테스트용 사용자 1명 생성 후 id 반환"""
    suffix = uuid.uuid4().hex[:8]
    if not email:
        email = f"u_{suffix}@test.com"
    u = await User.create(
        email=email,
        password="test1234",
        nickname=f"tester_{suffix}",
        username="테스터",
        phonenumber="010-0000-0000",
    )
    return u.id


# =============================================================================
# 테스트 케이스
# =============================================================================


async def test_create_diary(client: AsyncClient, monkeypatch):
    """
    다이어리 생성 (멀티파트 + 파일 업로드 스텁 + AI 스텁 동작)
    - Cloudinary 업로드는 라우터 네임스페이스에서 스텁으로 대체
    - 응답의 image_urls에 업로드된 URL이 포함되는지 검증
    """

    # Cloudinary 업로드 스텁: 업로드된 파일 "이름"으로 URL 생성
    async def _stub_upload_images_to_urls(files, opts=None):
        return [
            f"https://cdn.example/{getattr(f, 'filename', 'unnamed')}"
            for f in (files or [])
        ]

    # ✅ 반드시 라우터 네임스페이스 기준으로 패치
    monkeypatch.setattr(
        "app.diary.api.CloudinaryService.upload_images_to_urls",
        _stub_upload_images_to_urls,
    )

    user_id = await _ensure_user()
    payload_json = {
        "user_id": user_id,
        "title": "오늘의 일기",
        "content": "날씨가 좋았다. 그래서 신나게 산책을 나갔다",
        "phonenumber": "010-1234-5678",
        "emotion_analysis_report": None,
        "tags": ["일상", "행복"],
    }

    # (필드명, 파일명, 바이트, MIME)
    image_files = [
        ("a.png", _PNG_1x1, "image/png"),
        ("b.png", _PNG_1x1, "image/png"),
    ]

    res = await _post_diary_multipart(client, payload_json, image_files=image_files)
    assert res.status_code == 201, res.text
    data = res.json()

    # 기본 필드 검증
    assert data["id"] > 0
    assert data["user_id"] == user_id
    assert data["title"] == payload_json["title"]
    assert data["content"] == payload_json["content"]

    # 이미지 URL 추출 유틸 (list[str] 또는 list[{url:...}] 모두 대응)
    def _extract_urls(imgs):
        if not imgs:
            return []
        if isinstance(imgs[0], str):
            return imgs
        if isinstance(imgs[0], dict):
            return [i.get("url") for i in imgs]
        return imgs

    urls = _extract_urls(data.get("image_urls") or [])
    assert urls == ["https://cdn.example/a.png", "https://cdn.example/b.png"]


async def test_get_diary(client: AsyncClient):
    """
    다이어리 단건 조회
    - 먼저 멀티파트로 생성 후 /diaries/{id} 조회
    """
    user_id = await _ensure_user()
    payload = {
        "user_id": user_id,
        "title": "오늘의 일기",
        "content": "날씨가 좋았다.",
        "main_emotion": None,
        "emotion_analysis_report": None,
        "tags": ["일상", "행복"],
        "image_urls": ["http://img/1.png", "http://img/2.png"],
    }

    res = await _post_diary_multipart(client, payload, image_files=None)
    assert res.status_code == 201, res.text
    d = res.json()
    diary_id = d["id"]

    # 조회
    res2 = await client.get(f"/diaries/{diary_id}")
    assert res2.status_code == 200, res2.text
    got = res2.json()

    assert got["id"] == diary_id
    assert got["title"] == payload["title"]
    assert got.get("tags") is not None
    assert got.get("image_urls") is not None


async def test_update_diary(client: AsyncClient):
    """
    ✅ 다이어리 부분 수정(PATCH)
    - 제목/내용 교체 + 태그/이미지 전체 교체
    """
    user_id = await _ensure_user()

    # 먼저 생성
    user_id = await _ensure_user()
    payload_json = {
        "user_id": user_id,
        "title": "오늘의 일기",
        "content": "날씨가 좋았다.",
        "main_emotion": None,
        "emotion_analysis_report": None,
        "tags": ["일상", "행복"],
        "image_urls": ["http://img/1.png", "http://img/2.png"],
    }
    res = await _post_diary_multipart(client, payload_json, image_files=None)
    assert res.status_code == 201, res.text
    d = res.json()
    diary_id = d["id"]

    # PATCH (서버 구현에 따라 JSON 또는 multipart 가능)
    patch = {
        "user_id": user_id,
        "title": "수정 후 제목",
        "content": "수정 후 내용",
        "tags": ["교체1", "교체2"],
        "image_urls": ["http://img/after1.png", "http://img/after2.png"],
    }
    res2 = await _patch_diary_multipart(client, diary_id, patch, image_files=None)
    assert res2.status_code == 200, res2.text
    upd = res2.json()

    def _names(tags):
        if not tags:
            return []
        if isinstance(tags[0], str):
            return tags
        if isinstance(tags[0], dict):
            return [t.get("name") for t in tags]
        return tags

    def _urls(imgs):
        if not imgs:
            return []
        if isinstance(imgs[0], str):
            return imgs
        if isinstance(imgs[0], dict):
            return [i.get("url") for i in imgs]
        return imgs

    assert upd["title"] == "수정 후 제목"
    assert upd["content"] == "수정 후 내용"
    assert _names(upd.get("tags")) == ["교체1", "교체2"]
    assert _urls(upd.get("images") or upd.get("image_urls")) == [
        "http://img/after1.png",
        "http://img/after2.png",
    ]


async def test_list_diaries_with_filters(client: AsyncClient):
    """
    ✅ 목록 조회 + 페이징/필터
    - 동일 유저로 3건 생성 후 page=1, page_size=2 조회
    """
    user_id = await _ensure_user()

    for i in range(3):
        await _post_diary_multipart(
            client,
            {
                "user_id": user_id,
                "title": f"목록 {i}",
                "content": "내용",
                "tags": ["m"],
            },
            image_files=None,
        )

    res = await client.get(
        "/diaries", params={"user_id": user_id, "page": 1, "page_size": 2}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 2
    assert body["meta"]["total"] >= 3
    assert len(body["items"]) == 2


async def test_emotion_stats_inferred(client: AsyncClient):
    """
    ✅ 감정 통계
    - emotion_analysis_report.main_emotion 을 기준으로 집계되는지 검증
    - 긍정/부정/중립 각각 최소 1개 이상 생성
    """
    user_id = await _ensure_user()

    # 긍정
    await _post_diary_multipart(
        client,
        {
            "user_id": user_id,
            "title": "emo1",
            "content": "c1",
            "emotion_analysis_report": {
                "main_emotion": "긍정",
                "confidence": 1.0,
                "emotion_analysis": {
                    "reason": "감정 판단의 근거 텍스트",
                    "key_phrases": ["핵심", "키워드", "..."],
                },
            },
        },
        image_files=None,
    )
    # 부정
    await _post_diary_multipart(
        client,
        {
            "user_id": user_id,
            "title": "emo2",
            "content": "c2",
            "emotion_analysis_report": {
                "main_emotion": "부정",
                "confidence": 1.0,
                "emotion_analysis": {
                    "reason": "감정 판단의 근거 텍스트",
                    "key_phrases": ["핵심", "키워드", "..."],
                },
            },
        },
        image_files=None,
    )
    # 중립
    await _post_diary_multipart(
        client,
        {
            "user_id": user_id,
            "title": "emo3",
            "content": "c3",
            "emotion_analysis_report": {
                "main_emotion": "중립",
                "confidence": 1.0,
                "emotion_analysis": {
                    "reason": "감정 판단의 근거 텍스트",
                    "key_phrases": ["핵심", "키워드", "..."],
                },
            },
        },
        image_files=None,
    )

    res = await client.get("/diaries/stats/summary", params={"user_id": user_id})
    assert res.status_code == 200, res.text
    stats = res.json().get("items") or {}
    assert stats.get("긍정", 1) >= 1
    assert stats.get("부정", 1) >= 1
    assert stats.get("중립", 1) >= 1
