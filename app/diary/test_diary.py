import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.diary.api import router as diary_router
from app.user.model import User

# ------------------------------
# 테스트용 간단 User/Tag 모델 (실제 앱 모델로 대체 가능)
# ------------------------------
# class User(Model):
#     id = fields.IntField(pk=True)
#     email = fields.CharField(max_length=255, unique=True, null=False)

#     class Meta:
#         table = "users"


# class Tag(Model):
#     id = fields.IntField(pk=True)
#     name = fields.CharField(max_length=50, unique=True, null=False)

#     class Meta:
#         table = "tags"


# ------------------------------
# Pytest 설정
# ------------------------------
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="session")
async def app() -> AsyncGenerator[FastAPI, None]:
    """
    테스트용 FastAPI 앱 구성 (운영 코드와 분리)
    - in-memory sqlite 사용
    - 실제 다이어리 라우터 mount
    - Tortoise는 테스트에서 직접 init
    """
    app = FastAPI(title="Test Diary API")
    app.include_router(diary_router)
    yield app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    """
    테스트 클라이언트
    - Tortoise ORM 직접 초기화 (register_tortoise 사용 안 함)
    """
    await Tortoise.init(
        config={
            "connections": {"default": "sqlite://:memory:"},
            "apps": {
                "models": {
                    "models": [
                        "app.user.model",  # User
                        "app.tag.model",  # Tag
                        "app.diary.model",  # Diary, Image, DiaryTag
                        "app.notification.model",  # Notification
                        "aerich.models",  # 마이그레이션용
                    ],
                    "default_connection": "default",
                }
            },
            "use_tz": True,
            "timezone": "Asia/Seoul",
        },
    )
    await Tortoise.generate_schemas()

    # httpx AsyncClient 준비
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await Tortoise.close_connections()  # type: ignore[attr-defined]


# ------------------------------
# 헬퍼: 유저 생성
# ------------------------------
async def _ensure_user(email: str = "") -> int:
    if not email:
        email = f"u_{uuid.uuid4().hex[:8]}@test.com"
    u = await User.create(
        email=email,
        password="test1234",
        nickname="tester",
        username="테스터",
        phonenumber="010-0000-0000",
    )
    return u.id


# ------------------------------
# 테스트: 다이어리 생성
# ------------------------------
async def test_create_diary(client: AsyncClient):
    user_id = await _ensure_user()

    payload = {
        "user_id": user_id,
        "title": "오늘의 일기",
        "content": "날씨가 좋았다.",
        "phonenumber": "010-1234-5678",
        "main_emotion": None,  # 미지정 → null
        "emotion_analysis": {
            "label": None,
            "positive": 0.7,
            "negative": 0.1,
            "neutral": 0.2,
        },
        "tags": ["일상", "행복"],
        "images": ["http://img/1.png", "http://img/2.png"],
    }

    res = await client.post("/diaries", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()

    # 필수 필드 검증
    assert data["diary_id"] > 0
    assert data["user_id"] == user_id
    assert data["title"] == payload["title"]
    assert data["content"] == payload["content"]
    assert data["main_emotion"] is None  # 미지정이면 null
    assert data["emotion_analysis"]["positive"] == 0.7

    # 관계 필드 검증
    assert [t["name"] for t in data["tags"]] == ["일상", "행복"]
    assert [i["url"] for i in data["images"]] == [
        "http://img/1.png",
        "http://img/2.png",
    ]


async def test_get_diary(client: AsyncClient):
    user_id = await _ensure_user()

    # 먼저 생성
    res = await client.post(
        "/diaries",
        json={
            "user_id": user_id,
            "title": "조회 테스트",
            "content": "내용",
            "tags": ["A"],
            "images": ["http://img/a.png"],
        },
    )
    d = res.json()
    diary_id = d["diary_id"]

    # 조회
    res2 = await client.get(f"/diaries/{diary_id}")
    assert res2.status_code == 200, res2.text
    got = res2.json()

    assert got["diary_id"] == diary_id
    assert got["title"] == "조회 테스트"
    assert got["tags"][0]["name"] == "A"
    assert got["images"][0]["url"] == "http://img/a.png"


# ------------------------------
# 테스트: 다이어리 수정 (부분 수정 + 태그/이미지 교체)
# ------------------------------
async def test_update_diary(client: AsyncClient):
    user_id = await _ensure_user()

    # 생성
    res = await client.post(
        "/diaries",
        json={
            "user_id": user_id,
            "title": "수정 전 제목",
            "content": "수정 전 내용",
            "tags": ["초기"],
            "images": ["http://img/before.png"],
        },
    )
    d = res.json()
    diary_id = d["diary_id"]

    # PATCH: 제목/내용 변경 + 태그/이미지 전체 교체
    patch = {
        "title": "수정 후 제목",
        "content": "수정 후 내용",
        "tags": ["교체1", "교체2"],
        "images": ["http://img/after1.png", "http://img/after2.png"],
        # main_emotion/emotion_analysis는 생략 (부분 수정 가능)
    }
    res2 = await client.patch(f"/diaries/{diary_id}", json=patch)
    assert res2.status_code == 200, res2.text
    upd = res2.json()

    assert upd["title"] == "수정 후 제목"
    assert upd["content"] == "수정 후 내용"
    assert [t["name"] for t in upd["tags"]] == ["교체1", "교체2"]
    assert [i["url"] for i in upd["images"]] == [
        "http://img/after1.png",
        "http://img/after2.png",
    ]


# ------------------------------
# 테스트: 목록 조회 + 페이징/필터
# ------------------------------
async def test_list_diaries_with_filters(client: AsyncClient):
    user_id = await _ensure_user()

    # 3건 생성
    for i in range(3):
        await client.post(
            "/diaries",
            json={
                "user_id": user_id,
                "title": f"목록 {i}",
                "content": "내용",
                "tags": ["m"],
            },
        )

    # 페이지 1 / 페이지당 2
    res = await client.get(
        "/diaries", params={"user_id": user_id, "page": 1, "page_size": 2}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 2
    assert body["meta"]["total"] >= 3
    assert len(body["items"]) == 2


# ------------------------------
# 테스트: 감정 통계 (main_emotion 미지정 시 분석 추론)
# ------------------------------
async def test_emotion_stats_inferred(client: AsyncClient):
    user_id = await _ensure_user()

    # 긍정 추론 케이스
    await client.post(
        "/diaries",
        json={
            "user_id": user_id,
            "title": "emo1",
            "content": "c1",
            "emotion_analysis": {"positive": 0.9, "negative": 0.05, "neutral": 0.05},
        },
    )
    # 부정 추론 케이스
    await client.post(
        "/diaries",
        json={
            "user_id": user_id,
            "title": "emo2",
            "content": "c2",
            "emotion_analysis": {"positive": 0.1, "negative": 0.8, "neutral": 0.1},
        },
    )
    # 중립 추론 케이스
    await client.post(
        "/diaries",
        json={
            "user_id": user_id,
            "title": "emo3",
            "content": "c3",
            "emotion_analysis": {"positive": 0.2, "negative": 0.2, "neutral": 0.6},
        },
    )

    res = await client.get(
        "/diaries/stats/summary", params={"user_id": user_id, "inferred": True}
    )
    assert res.status_code == 200
    stats = res.json()["items"]

    # 최소한 세 감정이 각각 1개 이상 카운트 되는지 확인
    assert stats.get("긍정", 0) >= 1
    assert stats.get("부정", 0) >= 1
    assert stats.get("중립", 0) >= 1
