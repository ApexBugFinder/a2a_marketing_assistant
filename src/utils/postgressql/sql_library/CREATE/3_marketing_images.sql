CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS "public"."marketing_images" (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     research_project_id UUID REFERENCES public.research_projects(id) ON DELETE CASCADE,
     image_url TEXT NOT NULL,
     tiny_url TEXT,
     description TEXT,
     size_bytes INTEGER,
     img_dimensions TEXT,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     saved_to_s3_at TIMESTAMP,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);