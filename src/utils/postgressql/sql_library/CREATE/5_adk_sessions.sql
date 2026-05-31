CREATE TABLE IF NOT EXISTS "public"."adk_sessions" (
    id          TEXT        NOT NULL,
    app_name    TEXT        NOT NULL,
    user_id     TEXT        NOT NULL,
    state       JSONB       NOT NULL DEFAULT '{}',
    events      JSONB       NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (app_name, user_id, id)
);