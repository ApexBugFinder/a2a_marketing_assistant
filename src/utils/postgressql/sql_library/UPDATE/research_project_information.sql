UPDATE public.research_project_information
SET research_topic = $2, research_overview = $3, research_objectives = $4,
    research_scope = $5, research_framework = $6,
    report_info = CAST($7 AS JSONB), summary_info = CAST($8 AS JSONB),
    research_project_id = $9, bottom_count = $10, updated_at = CURRENT_TIMESTAMP
WHERE id = $1
RETURNING *;