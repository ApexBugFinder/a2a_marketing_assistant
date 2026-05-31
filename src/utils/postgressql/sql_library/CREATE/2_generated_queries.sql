CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS "public"."generated_queries" (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     research_project_id UUID REFERENCES public.research_projects(id) ON DELETE CASCADE,
     generated_query TEXT NOT NULL,
     research_cycle_count INTEGER NOT NULL DEFAULT 0,
     framework_category TEXT NOT NULL,
     status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'verified', 'searched')),
     created_at BIGINT NOT NULL DEFAULT CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT),
     updated_at BIGINT NOT NULL DEFAULT CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT)
     );