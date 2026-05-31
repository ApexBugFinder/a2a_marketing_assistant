SELECT * FROM "public"."linkedin_posts"
WHERE research_project_id = $1
ORDER BY created_at DESC;