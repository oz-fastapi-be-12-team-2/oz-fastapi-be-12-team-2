from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "emotion_stats" (
    "stat_id" SERIAL NOT NULL PRIMARY KEY,
    "period_type" VARCHAR(2) NOT NULL,
    "emotion_type" VARCHAR(2) NOT NULL,
    "frequency" INT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "emotion_stats"."period_type" IS 'DAILY: 일간\nWEEKLY: 주간';
COMMENT ON COLUMN "emotion_stats"."emotion_type" IS 'POSITIVE: 긍정\nNEGATIVE: 부정\nNEUTRAL: 중립';
        ALTER TABLE "users" ADD "receive_notifications" BOOL NOT NULL DEFAULT True;
        ALTER TABLE "users" ADD "notification_type" VARCHAR(5) NOT NULL DEFAULT 'PUSH';
        ALTER TABLE "감정 알림" RENAME TO "notifications";
        ALTER TABLE "notifications" RENAME COLUMN "alert_id" TO "notification_id";
        ALTER TABLE "notifications" ADD "notification_type" VARCHAR(5) NOT NULL DEFAULT 'EMAIL';
        ALTER TABLE "notifications" DROP COLUMN "alert_type";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" DROP COLUMN "receive_notifications";
        ALTER TABLE "users" DROP COLUMN "notification_type";
        ALTER TABLE "notifications" RENAME TO "감정 알림";
        ALTER TABLE "notifications" RENAME COLUMN "notification_id" TO "alert_id";
        ALTER TABLE "notifications" ADD "alert_type" VARCHAR(5) NOT NULL;
        ALTER TABLE "notifications" DROP COLUMN "notification_type";
        DROP TABLE IF EXISTS "emotion_stats";"""
