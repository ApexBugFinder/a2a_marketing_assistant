CREATE TABLE IF NOT EXISTS "public".blog_content (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     research_project_id UUID REFERENCES public.research_projects(id) ON DELETE CASCADE,
     title TEXT,
     content TEXT,
     seo_keywords TEXT,
     blog_status TEXT,
     publication_date TIMESTAMP,
     blog_url TEXT,
     keywords_and_key_aspects TEXT,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);