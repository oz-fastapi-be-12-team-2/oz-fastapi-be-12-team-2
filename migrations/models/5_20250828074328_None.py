from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "감정 알림" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "alert_id" BIGSERIAL NOT NULL PRIMARY KEY,
    "content" VARCHAR(255),
    "alert_type" VARCHAR(5) NOT NULL
);
COMMENT ON COLUMN "감정 알림"."alert_type" IS 'PUSH: PUSH\nEMAIL: EMAIL\nSMS: SMS';
CREATE TABLE IF NOT EXISTS "users" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "nickname" VARCHAR(20) NOT NULL UNIQUE,
    "email" VARCHAR(100) NOT NULL UNIQUE,
    "password" VARCHAR(255) NOT NULL,
    "username" VARCHAR(20) NOT NULL,
    "phonenumber" VARCHAR(20) NOT NULL,
    "lastlogin" TIMESTAMPTZ,
    "account_activation" BOOL NOT NULL DEFAULT False,
    "user_roles" VARCHAR(9) NOT NULL DEFAULT 'user'
);
COMMENT ON COLUMN "users"."user_roles" IS 'USER: user\nSTAFF: staff\nSUPERUSER: superuser';
CREATE TABLE IF NOT EXISTS "diaries" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(50) NOT NULL,
    "content" TEXT NOT NULL,
    "emotion_analysis" TEXT,
    "main_emotion" VARCHAR(2),
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "diaries"."main_emotion" IS 'POSITIVE: 긍정\nNEGATIVE: 부정\nNEUTRAL: 중립';
CREATE TABLE IF NOT EXISTS "images" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "order" INT NOT NULL,
    "image" TEXT NOT NULL,
    "diary_id" BIGINT NOT NULL REFERENCES "diaries" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "tags" (
    "tag_id" BIGSERIAL NOT NULL PRIMARY KEY,
    "tag_name" VARCHAR(50) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "감정 알림_users" (
    "감정 알림_id" BIGINT NOT NULL REFERENCES "감정 알림" ("alert_id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_감정 알림_users_감정 알림_i_1cd8f2" ON "감정 알림_users" ("감정 알림_id", "user_id");
CREATE TABLE IF NOT EXISTS "diary_tag" (
    "diaries_id" BIGINT NOT NULL REFERENCES "diaries" ("id") ON DELETE CASCADE,
    "tag_id" BIGINT NOT NULL REFERENCES "tags" ("tag_id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_diary_tag_diaries_dc5517" ON "diary_tag" ("diaries_id", "tag_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
