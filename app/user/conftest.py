import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from tortoise.contrib.test import finalizer, initializer

from app.main import app


@pytest.fixture(scope="module", autouse=True)
def initialize_tests():
    """
    테스트 전용 DB 초기화 (SQLite in-memory)
    """
    os.environ["TESTING"] = "1"

    initializer(["app.user.model"], db_url="sqlite://:memory:")
    yield
    finalizer()


@pytest_asyncio.fixture
async def async_client():
    """
    FastAPI 앱을 테스트할 때 사용하는 HTTP 클라이언트
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
