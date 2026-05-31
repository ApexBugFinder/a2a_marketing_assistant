CREATE TABLE IF NOT EXISTS "public".blog_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_project_id UUID REFERENCES public.research_projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    seo_keywords TEXT[] DEFAULT '{}',
    publication_date BIGINT,
    keywords_and_key_aspects TEXT[] DEFAULT '{}',
    metadata JSONB NOT NULL
);
