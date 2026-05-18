CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS "public"."marketing_images" (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     research_project_id UUID REFERENCES public.research_projects(id) ON DELETE CASCADE,
     image_url TEXT NOT NULL,
     tiny_url TEXT,
     description TEXT,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     );