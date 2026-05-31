CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.research_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_project_id UUID NOT NULL REFERENCES public.research_projects(id) ON DELETE CASCADE,
    source TEXT,
    pub_date TEXT,
    title TEXT,
    url TEXT,
    research_cycle_count INTEGER
);