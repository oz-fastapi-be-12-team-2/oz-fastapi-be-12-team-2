from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
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
    "receive_notifications" BOOL NOT NULL DEFAULT True,
    "user_roles" VARCHAR(9) NOT NULL DEFAULT 'user'
);
COMMENT ON COLUMN "users"."user_roles" IS 'USER: user\nSTAFF: staff\nSUPERUSER: superuser';
CREATE TABLE IF NOT EXISTS "diaries" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(50) NOT NULL,
    "content" TEXT NOT NULL,
    "emotion_analysis_report" JSONB,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_diaries_title_664dc3" ON "diaries" ("title");
COMMENT ON COLUMN "diaries"."emotion_analysis_report" IS 'AI 감정 분석 리포트(JSON: main_emotion, confidence, emotion_analysis{reason,key_phrases})';
CREATE TABLE IF NOT EXISTS "images" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "order" INT NOT NULL,
    "url" TEXT NOT NULL,
    "diary_id" BIGINT NOT NULL REFERENCES "diaries" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_images_diary_i_e7a50b" UNIQUE ("diary_id", "order")
);
CREATE INDEX IF NOT EXISTS "idx_images_order_dffd3a" ON "images" ("order");
CREATE INDEX IF NOT EXISTS "idx_images_diary_i_f390f6" ON "images" ("diary_id");
CREATE TABLE IF NOT EXISTS "emotion_stats" (
    "stat_id" SERIAL NOT NULL PRIMARY KEY,
    "period_type" VARCHAR(2) NOT NULL,
    "emotion_type" VARCHAR(2) NOT NULL,
    "frequency" INT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_emotion_sta_user_id_ce801c" ON "emotion_stats" ("user_id");
COMMENT ON COLUMN "emotion_stats"."period_type" IS 'DAILY: 일간\nWEEKLY: 주간';
COMMENT ON COLUMN "emotion_stats"."emotion_type" IS 'POSITIVE: 긍정\nNEGATIVE: 부정\nNEUTRAL: 중립';
CREATE TABLE IF NOT EXISTS "tags" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(50) NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS "idx_tags_name_15558f" ON "tags" ("name");
COMMENT ON TABLE "tags" IS '태그 모델';
CREATE TABLE IF NOT EXISTS "diary_tag" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "diary_id" BIGINT NOT NULL REFERENCES "diaries" ("id") ON DELETE CASCADE,
    "tag_id" INT NOT NULL REFERENCES "tags" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_diary_tag_diary_i_47c64b" UNIQUE ("diary_id", "tag_id")
);
CREATE INDEX IF NOT EXISTS "idx_diary_tag_diary_i_0fa63c" ON "diary_tag" ("diary_id");
CREATE INDEX IF NOT EXISTS "idx_diary_tag_tag_id_5bea5d" ON "diary_tag" ("tag_id");
CREATE INDEX IF NOT EXISTS "idx_diary_tag_diary_i_47c64b" ON "diary_tag" ("diary_id", "tag_id");
COMMENT ON TABLE "diary_tag" IS 'Diary - Tag 조인 테이블.';
CREATE TABLE IF NOT EXISTS "notification" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "content" VARCHAR(255),
    "notification_type" VARCHAR(5) NOT NULL DEFAULT 'EMAIL'
);
COMMENT ON COLUMN "notification"."notification_type" IS 'PUSH: PUSH\nEMAIL: EMAIL\nSMS: SMS';
CREATE TABLE IF NOT EXISTS "user_notification" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "notification_id" BIGINT NOT NULL REFERENCES "notification" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_user_notifi_user_id_d6887e" UNIQUE ("user_id", "notification_id")
);
CREATE INDEX IF NOT EXISTS "idx_user_notifi_notific_3d832b" ON "user_notification" ("notification_id");
CREATE INDEX IF NOT EXISTS "idx_user_notifi_user_id_40d987" ON "user_notification" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_user_notifi_user_id_d6887e" ON "user_notification" ("user_id", "notification_id");
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "models.UserNotification" (
    "users_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    "notification_id" BIGINT NOT NULL REFERENCES "notification" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_models.User_users_i_b77d28" ON "models.UserNotification" ("users_id", "notification_id");
CREATE TABLE IF NOT EXISTS "models.DiaryTag" (
    "diaries_id" BIGINT NOT NULL REFERENCES "diaries" ("id") ON DELETE CASCADE,
    "tag_id" INT NOT NULL REFERENCES "tags" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_models.Diar_diaries_b4a6c0" ON "models.DiaryTag" ("diaries_id", "tag_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
