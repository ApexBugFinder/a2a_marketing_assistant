CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS "public"."generated_queries" (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     research_project_id UUID REFERENCES public.research_projects(id) ON DELETE CASCADE,
     generated_query TEXT NOT NULL,
     research_cycle_count INTEGER NOT NULL,
     framework_category TEXT,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     );