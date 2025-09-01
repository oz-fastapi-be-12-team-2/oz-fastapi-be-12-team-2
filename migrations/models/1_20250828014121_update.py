from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "감정 알림" RENAME TO "notifications";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "notifications" RENAME TO "감정 알림";"""
