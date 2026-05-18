CREATE TABLE IF NOT EXISTS public.research_project_information (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_project_id UUID REFERENCES public.research_projects(id) ON DELETE CASCADE,
    research_topic TEXT,
    research_overview TEXT,
    research_objectives TEXT,
    research_scope TEXT,
    research_framework TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);