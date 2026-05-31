INSERT INTO public.research_project_information
    (id, research_project_id, research_topic, research_overview,
     research_objectives, research_scope, research_framework, report_info, summary_info, bottom_count)
VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7, CAST($8 AS JSONB), CAST($9 AS JSONB), $10)
RETURNING *;
