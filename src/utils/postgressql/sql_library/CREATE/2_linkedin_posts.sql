CREATE TABLE IF NOT EXISTS public.linkedin_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_urn TEXT NOT NULL,
    text TEXT NOT NULL,
    hashtags TEXT[] DEFAULT '{}',
    image_url TEXT,
    linkedin_post_id TEXT,
    scheduled_time BIGINT,
    research_project_id UUID REFERENCES public.research_projects(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
