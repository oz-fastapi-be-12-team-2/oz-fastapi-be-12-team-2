from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
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
        CREATE TABLE IF NOT EXISTS "tags" (
    "tag_id" BIGSERIAL NOT NULL PRIMARY KEY,
    "tag_name" VARCHAR(50) NOT NULL UNIQUE
);
        CREATE TABLE IF NOT EXISTS "감정 알림" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "alert_id" BIGSERIAL NOT NULL PRIMARY KEY,
    "content" VARCHAR(255),
    "alert_type" VARCHAR(5) NOT NULL
);
COMMENT ON COLUMN "감정 알림"."alert_type" IS 'PUSH: PUSH\nEMAIL: EMAIL\nSMS: SMS';
        CREATE TABLE "diary_tag" (
    "diaries_id" BIGINT NOT NULL REFERENCES "diaries" ("id") ON DELETE CASCADE,
    "tag_id" BIGINT NOT NULL REFERENCES "tags" ("tag_id") ON DELETE CASCADE
);
        CREATE TABLE "감정 알림_users" (
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    "감정 알림_id" BIGINT NOT NULL REFERENCES "감정 알림" ("alert_id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "users";
        DROP TABLE IF EXISTS "images";
        DROP TABLE IF EXISTS "tags";
        DROP TABLE IF EXISTS "diaries";
        DROP TABLE IF EXISTS "감정 알림";"""
