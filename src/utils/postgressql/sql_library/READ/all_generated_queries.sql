SELECT * FROM "public"."generated_queries"
WHERE research_project_id = %s
ORDER BY created_at DESC;