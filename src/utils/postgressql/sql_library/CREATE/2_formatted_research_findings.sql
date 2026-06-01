CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.formatted_research_findings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        research_project_id UUID NOT NULL  REFERENCES public.research_projects(id) ON DELETE CASCADE,
        source TEXT,
        finding_summary TEXT,
        title TEXT,
        author TEXT,
        relevance_to_research_topic TEXT,
        publication_date TEXT,
        source_url TEXT,
        keywords_and_key_aspects TEXT,
        research_cycle_count INTEGER,
        query TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);