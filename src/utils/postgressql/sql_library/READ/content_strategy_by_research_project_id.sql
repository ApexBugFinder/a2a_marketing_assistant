SELECT * FROM "public"."content_strategy"
WHERE research_project_id = $1
ORDER BY created_at DESC;