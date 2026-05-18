SELECT * FROM "public"."content_strategy"
WHERE research_id = $1
ORDER BY created_at DESC;