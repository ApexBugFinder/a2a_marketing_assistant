CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.linkedin_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    author_urn TEXT,
    email TEXT,
    access_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);