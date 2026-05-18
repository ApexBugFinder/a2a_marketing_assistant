CREATE TABLE IF NOT EXISTS content_strategy (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     research_project_id UUID NOT NULL,
     content_strategy TEXT NOT NULL,
     content_strategy_overview TEXT NOT NULL,
     key_messages TEXT NOT NULL,
     target_audience TEXT NOT NULL,
     content_formats_and_channels TEXT NOT NULL,
     content_strategy_calendar JSONB NOT NULL DEFAULT '[]'::jsonb,
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW(),
     FOREIGN KEY (research_project_id) REFERENCES research_projects(id) ON DELETE CASCADE
);
