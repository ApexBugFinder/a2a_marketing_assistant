SELECT * FROM "public"."generated_queries"
WHERE research_project_id = $1
ORDER BY created_at DESC;