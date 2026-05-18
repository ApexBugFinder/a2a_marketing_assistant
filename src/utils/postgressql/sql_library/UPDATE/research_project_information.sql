UPDATE "public".research_project_information
SET research_topic = $2, research_overview = $3, research_objectives = $4, research_scope = $5, research_framework = $6, research_project_id = $7, updated_at = CURRENT_TIMESTAMP
WHERE id = $1;